
import argparse
import os
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import tensorflow as tf


def read_image(image_path):
    image = tf.keras.preprocessing.image.load_img(image_path, target_size=(224,224))
    image = np.expand_dims(image, axis=0)
    image = tf.keras.applications.imagenet_utils.preprocess_input(image)
    return image


def retrieve_model(model_name):
    model_dict = {
        'resnet': tf.keras.applications.resnet50.ResNet50,
        'vgg': tf.keras.applications.vgg16.VGG16,
        'mobilenet': tf.keras.applications.mobilenet_v2.MobileNetV2
    }
    return model_dict[model_name](weights='imagenet')


def make_prediction(image, model):
    preds = model.predict(image)
    preds = tf.keras.applications.imagenet_utils.decode_predictions(preds=preds)

    return preds


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--path')
    parser.add_argument('--class', default='volcano')
    parser.add_argument('--model', default='mobilenet')

    args = vars(parser.parse_args())

    image = read_image(args['path'])
    model = retrieve_model(args['model'])
    preds = make_prediction(image, model)

    if preds[0][0][1] != args['class']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
