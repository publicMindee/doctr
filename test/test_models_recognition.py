import pytest
import numpy as np
import math
import tensorflow as tf

from doctr.models import recognition
from doctr.documents import DocumentFile
from doctr.models import extract_crops


def test_recopreprocessor(mock_pdf):  # noqa: F811
    num_docs = 3
    batch_size = 4
    docs = [DocumentFile.from_pdf(mock_pdf).as_images() for _ in range(num_docs)]
    processor = recognition.RecognitionPreProcessor(output_size=(256, 128), batch_size=batch_size)
    batched_docs = processor([page for doc in docs for page in doc])

    # Number of batches
    assert len(batched_docs) == math.ceil(8 * num_docs / batch_size)
    # Total number of samples
    assert sum(batch.shape[0] for batch in batched_docs) == 8 * num_docs
    # Batch size
    assert all(batch.shape[0] == batch_size for batch in batched_docs[:-1])
    assert batched_docs[-1].shape[0] == batch_size if (8 * num_docs) % batch_size == 0 else (8 * num_docs) % batch_size
    # Data type
    assert all(batch.dtype == tf.float32 for batch in batched_docs)
    # Image size
    assert all(batch.shape[1:] == (256, 128, 3) for batch in batched_docs)
    # Test with non-full last batch
    batch_size = 16
    processor = recognition.RecognitionPreProcessor(output_size=(256, 128), batch_size=batch_size)
    batched_docs = processor([page for doc in docs for page in doc])
    assert batched_docs[-1].shape[0] == (8 * num_docs) % batch_size
    # Repr
    assert repr(processor) == 'RecognitionPreProcessor(output_size=(256, 128), mean=[0.5 0.5 0.5], std=[1. 1. 1.])'


@pytest.mark.parametrize(
    "arch_name, input_shape, output_size",
    [
        ["crnn_vgg16_bn", (32, 128, 3), (32, 119)],
        ["sar_vgg16_bn", (32, 128, 3), (31, 119)],
        ["sar_resnet31", (32, 128, 3), (31, 119)],
        ["crnn_resnet31", (32, 128, 3), (32, 119)],
    ],
)
def test_recognition_models(arch_name, input_shape, output_size):
    batch_size = 8
    reco_model = recognition.__dict__[arch_name](pretrained=True, input_shape=input_shape)
    input_tensor = tf.random.uniform(shape=[batch_size, *input_shape], minval=0, maxval=1)
    out = reco_model(input_tensor)
    assert isinstance(out, tf.Tensor)
    assert isinstance(reco_model, tf.keras.Model)
    assert out.numpy().shape == (batch_size, *output_size)


def test_sar_training():
    batch_size = 4
    input_shape = (32, 128, 3)
    output_size = (31, 119)
    reco_model = recognition.sar_vgg16_bn(input_shape=input_shape)
    input_tensor = tf.random.uniform(shape=[batch_size, *input_shape], minval=0, maxval=1)
    # input_labels: sparse_tensor of shape batch_size x max_len, encoding the labels
    # filled with integers (classes of the characters at each timestep)
    indices = [[0, 0], [0, 1], [1, 0], [1, 1], [1, 2], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [3, 4]]
    values = tf.random.uniform(shape=[11], minval=0, maxval=118, dtype=tf.dtypes.int64)
    input_labels = tf.sparse.reorder(
        tf.sparse.SparseTensor(indices=indices, values=values, dense_shape=[batch_size, 31])
    )
    input_dense = tf.sparse.to_dense(input_labels, default_value=118)
    out = reco_model(input_tensor, labels=input_dense, training=True)
    assert isinstance(out, tf.Tensor)
    assert isinstance(reco_model, tf.keras.Model)
    assert out.numpy().shape == (batch_size, *output_size)


@pytest.mark.parametrize(
    "post_processor, input_shape",
    [
        ["SARPostProcessor", [2, 30, 119]],
        ["CTCPostProcessor", [2, 30, 119]],
    ],
)
def test_reco_postprocessors(post_processor, input_shape, mock_vocab):
    processor = recognition.__dict__[post_processor](mock_vocab)
    decoded = processor(tf.random.uniform(shape=input_shape, minval=0, maxval=1, dtype=tf.float32))
    assert isinstance(decoded, list) and all(isinstance(word, str) for word in decoded)
    assert len(decoded) == input_shape[0]
    assert all(char in mock_vocab for word in decoded for char in word)
    # Repr
    assert repr(processor) == f'{post_processor}(vocab_size={len(mock_vocab)})'


@pytest.fixture(scope="session")
def test_recognitionpredictor(mock_pdf, mock_vocab):  # noqa: F811

    batch_size = 4
    predictor = recognition.RecognitionPredictor(
        recognition.RecognitionPreProcessor(output_size=(32, 128), batch_size=batch_size),
        recognition.crnn_vgg16_bn(vocab=mock_vocab, input_shape=(32, 128, 3)),
        recognition.CTCPostProcessor(mock_vocab)
    )

    pages = DocumentFile.from_pdf(mock_pdf).as_images()
    # Create bounding boxes
    boxes = np.array([[0, 0, 0.25, 0.25], [0.5, 0.5, 1., 1.]], dtype=np.float32)
    crops = extract_crops(pages[0], boxes)

    out = predictor(crops)

    # One prediction per crop
    assert len(out) == boxes.shape[0]
    assert all(isinstance(charseq, str) for charseq in out)

    # Dimension check
    with pytest.raises(ValueError):
        input_crop = (255 * np.random.rand(1, 128, 64, 3)).astype(np.uint8)
        _ = predictor([input_crop])

    return predictor


@pytest.mark.parametrize(
    "arch_name",
    [
        "crnn_vgg16_bn",
        "sar_vgg16_bn",
        "sar_resnet31",
        "crnn_resnet31",
    ],
)
def test_recognition_zoo(arch_name):
    batch_size = 2
    # Model
    predictor = recognition.zoo.recognition_predictor(arch_name, pretrained=False)
    # object check
    assert isinstance(predictor, recognition.RecognitionPredictor)
    input_tensor = tf.random.uniform(shape=[batch_size, 1024, 1024, 3], minval=0, maxval=1)
    out = predictor(input_tensor)
    assert isinstance(out, list) and len(out) == batch_size
    assert all(isinstance(word, str) for word in out)


def test_recognition_zoo_error():
    with pytest.raises(ValueError):
        _ = recognition.zoo.recognition_predictor("my_fancy_model", pretrained=False)


def test_compute_loss_sar():
    list_gts = ['elephants', '1234', 'Rémouleur']
    model_input = tf.random.uniform(shape=[3, 32, 128, 3], minval=0, maxval=1)
    model = recognition.sar_vgg16_bn()
    model_output = model(model_input)
    encoded_gts, seq_len = model.compute_target(list_gts)
    assert isinstance(encoded_gts, tf.Tensor)
    assert isinstance(seq_len, tf.Tensor)
    assert list(seq_len.numpy()) == [9, 4, 9]
    loss = model.compute_loss(encoded_gts, model_output, seq_len)
    assert isinstance(loss, tf.Tensor)


def test_compute_loss_crnn():
    list_gts = ['elephants', '1234', 'Rémouleur']
    model_input = tf.random.uniform(shape=[3, 32, 128, 3], minval=0, maxval=1)
    model = recognition.crnn_vgg16_bn()
    model_output = model(model_input)
    encoded_gts, seq_len = model.compute_target(list_gts)
    assert isinstance(encoded_gts, tf.Tensor)
    assert isinstance(seq_len, tf.Tensor)
    assert list(seq_len.numpy()) == [9, 4, 9]
    loss = model.compute_loss(encoded_gts, model_output, seq_len)
    assert isinstance(loss, tf.Tensor)
