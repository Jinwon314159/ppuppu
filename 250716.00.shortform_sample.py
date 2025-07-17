# -*- coding: utf-8 -*-
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 해상도
width, height = 1080, 1920

def create_text_image(text, size=(width, height), font_size=180):
    img = Image.new("RGBA", size, (255, 255, 255, 0))  # 투명 배경
    draw = ImageDraw.Draw(img)

    # ✅ macOS 기본 한글 폰트 사용
    font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", font_size)

    # 텍스트 크기 계산 및 가운데 정렬
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)

    draw.text(position, text, font=font, fill="black")
    return np.array(img)

# 텍스트 이미지 → ImageClip 변환
text_img = create_text_image("샘플 텍스트")
text_clip = ImageClip(text_img).set_duration(3)

# 배경 클립
bg = ColorClip((width, height), color=(255, 255, 255), duration=3)

# 합성
final = CompositeVideoClip([bg, text_clip.set_position('center')])

# 🎬 영상 저장 (H.264, 24fps)
final.write_videofile(
    "shortform_sample.mp4",
    fps=24,
    codec="libx264",
    audio=False,
    preset="medium"
)
