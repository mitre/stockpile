
import argparse
import glob
import os
import sys
import numpy as np
import tensorflow as tf

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

IMAGE_FILE_TYPES = ['.png', '.jpeg', '.jpg', '.gif']
TARGET_IMAGE_SIZE = (224, 224)


# TODO: Test off enterprise, VPN killing tensorflow SSL web requests


def read_image(image_path: str) -> np.ndarray:
    image = tf.keras.preprocessing.image.load_img(image_path, target_size=TARGET_IMAGE_SIZE)
    image = np.expand_dims(image, axis=0)
    image = tf.keras.applications.imagenet_utils.preprocess_input(image)
    return image


def retrieve_model(model_name: str) -> dict:
    model_dict = {
        'resnet': tf.keras.applications.resnet50.ResNet50,
        'vgg': tf.keras.applications.vgg16.VGG16,
        'mobilenet': tf.keras.applications.mobilenet_v2.MobileNetV2
    }
    return model_dict[model_name](weights='imagenet')


def predict_class(image: np.ndarray, model):
    preds = model.predict(image)
    preds = tf.keras.applications.imagenet_utils.decode_predictions(preds=preds)
    return preds


def process_dir(path: str, model, target_class: str) -> list:
    matches = []
    for i in IMAGE_FILE_TYPES:
        for file_ in glob.glob(f'{path}/*.{i}', recursive=True):
            if process_file(file_, model, target_class):
                matches.append(f'{file_}\n')
    return matches


def process_file(file: np.ndarray, model, target_class) -> bool:
    preds = predict_class(read_image(file), model)
    return True if preds[0][0][1] != target_class else False


def get_argparser():
    parser = argparse.ArgumentParser()
    path = parser.add_mutually_exclusive_group(required=True)
    path.add_argument('--file')
    path.add_argument('--dir')
    parser.add_argument('--class', default='volcano')
    parser.add_argument('--model', default='mobilenet')
    return parser


def main():
    parser = get_argparser()
    args = vars(parser.parse_args())

    model = retrieve_model(args['model'])

    if args['file']:
        if process_file(args['file']):
            sys.stdout(args['file'])
    elif args['dir']:
        matches = process_dir(
            path=args['path'],
            model=model,
            target_class=args['class']
        )
        sys.stdout(matches)


if __name__ == '__main__':
    main()
