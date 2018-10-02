#!/usr/bin/env python

import os
import sys
import time
import math
import numpy as np
from PIL import Image
from numba import njit

from qtmodern import styles, windows
from PyQt5.QtGui import QPixmap, QColor, QPainter, QPen, QImage
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtWidgets import QWidget, QFileDialog, QDesktopWidget, QApplication, QLabel, QPushButton, QGridLayout, QColorDialog, QCheckBox

def time_dec(func):
    def wrapper(*args):
        start_time = time.time()
        func(*args)
        print(f"Execution time for {func.__name__} is {time.time() - start_time}s")
    return wrapper


@njit
def find_first(array, item):
    for idx, val in np.ndenumerate(array):
        if val != item:
            return idx
    return None

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """
        Initialize user interface
        """
        self.label = QLabel(self)
        self.pixmap = QPixmap(600, 600)
        self.pixmap.fill(Qt.white)
        self.label.setPixmap(self.pixmap)
        self.img = ''

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(10)
        self.setLayout(self.grid)
        self.points = np.empty(0)
        self.points_pos = []

        self.init_save_button()
        self.init_clean_button()
        self.init_choose_button()
        self.init_choose_color()
        self.init_fill_by_image()
        self.fill_grid()

        self.lastPoint = QPoint()
        self.fill_by_image = False
        self.color = [255, 21, 241, 255]

        self.center()
        
        
    def init_save_button(self):
        self.save_img = QPushButton('Save image', self)
        self.save_img.clicked.connect(self.save_img_on_click)

    def init_choose_button(self):
        self.choose_img = QPushButton('Choose image', self)
        self.choose_img.clicked.connect(self.choose_on_click)

    def init_choose_color(self):
        self.choose_color = QPushButton('Choose color', self)
        self.choose_color.clicked.connect(self.choose_color_clicked)
                                          
    def choose_color_clicked(self):
        color = QColorDialog.getColor() 
        if color.isValid():
            self.color = color.getRgb()[::-1][1:] + (255,)

    def init_clean_button(self):
        self.clean_pixmap = QPushButton('Clean', self)
        self.clean_pixmap.clicked.connect(self.clean_on_click)

    def init_fill_by_image(self):
        self.fill_by_image_box = QCheckBox('Fill by choosed image', self)
        self.fill_by_image_box.stateChanged.connect(self.change_fill_method)

    def change_fill_method(self, state):
        self.fill_by_image = state == Qt.Checked

    def clean_on_click(self):
        self.points = np.empty(0)
        self.pixmap.fill(Qt.white)
        self.label.setPixmap(self.pixmap)

    def choose_on_click(self):
        dialog = QFileDialog()
        filename, _ = dialog.getOpenFileName(self, filter="Images (*.jpg *.jpeg *.png)")
        self.filename = filename if filename else self.filename
        file_pixmap = QPixmap(self.filename).scaled(self.pixmap.width(), 
                                                    self.pixmap.height())
        self.image_array = self.pixmap_to_array(file_pixmap)


    def save_img_on_click(self):
        img = self.pixmap.toImage()
        img.save('pixmap.jpg')

    def extract_coords_from_pos(self, pos):
        x = pos.x()
        y = pos.y()
        return x, y
        
    def array_to_pixmap(self, array):
        image = QImage(array, array.shape[0], array.shape[1], QImage.Format_RGB32)
        return image

    def update_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.label.setPixmap(self.pixmap)

    @time_dec
    def fill_area(self, start_point):
        # Convert current QPixmap to numpy array
        self.pixels = self.pixmap_to_array(self.pixmap)

        # Modify
        self.line_fill(start_point[0], start_point[1], self.color)

        # Convert back to QImage, and then to QPixmap
        image = self.array_to_pixmap(self.pixels)

        # Update current pixmap
        self.update_pixmap(QPixmap.fromImage(image))

        
    def line_fill(self, x, y, color):
        if (np.all(self.pixels[y][x] != [255, 255, 255, 255]) or 
            np.any(self.pixels[y][x] == color)):
            exit

        left_point = x - 1 - find_first(self.pixels[y][:x][::-1], 255)[0]
        right_point = find_first(self.pixels[y][x:], 255)[0] + x

        if self.fill_by_image:
            try:
                self.pixels[y][left_point:right_point] = self.image_array[y][left_point:right_point]
            except Exception as e:
                print('Choose image')
                return
        else:
            self.pixels[y][left_point:right_point] = color
            
        for i in np.arange(left_point + 1, right_point - 1):
            self.line_fill(i, y - 1, color)
            self.line_fill(i, y + 1, color)
        

    def pixmap_to_array(self, pixmap):
        image = pixmap.toImage().convertToFormat(QImage.Format_RGB32)
        buff = image.bits().asstring(self.pixmap.width() * self.pixmap.height() * 4)
        array = np.frombuffer(buff, dtype=np.uint8).reshape(self.pixmap.width(), self.pixmap.height(), 4) 
        array.setflags(write=1)
        return array

    def transform_pos(self, pos):
        x, y = self.extract_coords_from_pos(pos)
        return (x - self.label.x(), y - self.label.y())
    
    def is_pos_in_label(self, pos):
        x, y = self.transform_pos(pos)
        width = self.label.width()
        height = self.label.height()
        return x in range(0, width) and y in range(0, height)

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton 
            and self.is_pos_in_label(event.pos())):
            x, y = self.transform_pos(event.pos())
            self.points = np.append(self.points, np.array(QPoint(x, y)))
            self.lastPoint = QPoint(x, y)

        if (event.button() == Qt.RightButton 
            and self.is_pos_in_label(event.pos())):
            self.fill_area(self.transform_pos(event.pos()))

    def mouseMoveEvent(self, event):
        if ((event.buttons() & Qt.LeftButton) and 
            self.is_pos_in_label(event.pos())):
            x, y = self.transform_pos(event.pos())
            self.points = np.append(self.points, QPoint(x, y))
            self.drawLineTo(QPoint(x, y))

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.LeftButton and 
            self.is_pos_in_label(event.pos())):
            x, y = self.transform_pos(event.pos())
            self.points = np.append(self.points, QPoint(x, y))
            self.drawLineTo(QPoint(x, y))
            self.scrabbling = False

    def drawLineTo(self, endPoint):
        painter = QPainter(self.pixmap)
        painter.setPen(QPen(Qt.black, 5.0))
        painter.drawLine(self.lastPoint, endPoint)
        self.lastPoint = QPoint(endPoint)
        self.label.setPixmap(self.pixmap)

    def drawPoints(self):
        if not self.points.size:
            print('exit')
            self.label.setPixmap(self.pixmap)
            return
        self.painter.setPen(QPen(Qt.black, 0.5))
        size = self.size()
 
        for i, p in enumerate(self.points[:-1]):
            next_point = self.points[i + 1]
            if ((p.x() != -1 and p.y() != -1) and 
                (next_point.x() != -1 and next_point.y() != -1)):
                self.painter.drawLine(p.x(), p.y(), next_point.x(), next_point.y())

    def fill_grid(self):
        self.grid.addWidget(self.save_img, 0, 0)
        self.grid.addWidget(self.clean_pixmap, 1, 0)
        self.grid.addWidget(self.fill_by_image_box, 1, 1)
        self.grid.addWidget(self.choose_img, 2, 0)
        self.grid.addWidget(self.choose_color, 2, 1)
        self.grid.addWidget(self.label, 0, 2, 3, 1)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    styles.dark(app)
    mw = windows.ModernWindow(win)
    mw.show()
    # win.show()
    sys.exit(app.exec_())
