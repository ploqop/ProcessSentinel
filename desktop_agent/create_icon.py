from PIL import Image, ImageDraw
import os

def create_icon():
    # Создаем директорию gui, если она не существует
    gui_dir = os.path.join(os.path.dirname(__file__), 'gui')
    os.makedirs(gui_dir, exist_ok=True)
    
    # Создаем изображение 256x256 пикселей
    size = 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Рисуем круг
    circle_color = (255, 0, 0, 255)  # Красный цвет
    circle_bbox = (size * 0.1, size * 0.1, size * 0.9, size * 0.9)
    draw.ellipse(circle_bbox, fill=circle_color)
    
    # Рисуем щит
    shield_color = (255, 255, 255, 255)  # Белый цвет
    shield_points = [
        (size * 0.3, size * 0.3),  # Верхняя точка
        (size * 0.7, size * 0.3),  # Правая точка
        (size * 0.8, size * 0.5),  # Правая нижняя точка
        (size * 0.5, size * 0.8),  # Нижняя точка
        (size * 0.2, size * 0.5),  # Левая нижняя точка
    ]
    draw.polygon(shield_points, fill=shield_color)
    
    # Сохраняем иконку
    icon_path = os.path.join(gui_dir, 'icon.png')
    image.save(icon_path)
    print(f"Icon created at: {icon_path}")

if __name__ == '__main__':
    create_icon() 