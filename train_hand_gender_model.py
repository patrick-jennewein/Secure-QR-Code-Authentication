import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout

# === Paths and Parameters ===
img_height, img_width = 224, 224
batch_size = 32
epochs = 10

# Make sure this path matches where your male/female folders are
train_dir = "11k_hands_subset/train"

# === Image Data Generator ===
train_datagen = ImageDataGenerator(
    rescale=1. / 255,
    validation_split=0.2  # 20% of images will be used for validation
)

train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='categorical',
    subset='training'
)

val_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='categorical',
    subset='validation'
)

# === Model Architecture ===
model = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(img_height, img_width, 3)),
    MaxPooling2D(2, 2),

    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D(2, 2),

    Flatten(),
    Dropout(0.5),
    Dense(64, activation='relu'),
    Dense(2, activation='softmax')  # Output layer: [Male, Female]
])

# === Compile Model ===
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# === Train Model ===
model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=epochs
)

# === Save Model ===
model.save("hand_gender_model.h5")
print("✅ Model trained and saved as hand_gender_model.h5")
