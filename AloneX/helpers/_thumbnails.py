# Copyright (c) 2025 TeamshonaX
# Licensed under the MIT License.
# This file is make by @theshonabots
#SHONA - BOTS

import os
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)

from AloneX import config
from AloneX.helpers import Track


class Thumbnail:
    def __init__(self):
        self.width = 1280
        self.height = 720

        self.album_size = 450
        self.radius = 40

        self.font_title = ImageFont.truetype(
            "AloneX/helpers/Raleway-Bold.ttf",
            58,
        )

        self.font_artist = ImageFont.truetype(
            "AloneX/helpers/Inter-Light.ttf",
            38,
        )

        self.font_small = ImageFont.truetype(
            "AloneX/helpers/Inter-Light.ttf",
            30,
        )

    async def save_thumb(
        self,
        output_path: str,
        url: str,
    ) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                open(output_path, "wb").write(
                    await resp.read()
                )
        return output_path

    def trim_text(
        self,
        text,
        font,
        max_width,
    ):
        if font.getlength(text) <= max_width:
            return text

        dots = "..."

        for i in range(len(text), 0, -1):
            temp = text[:i] + dots

            if font.getlength(temp) <= max_width:
                return temp

        return dots

    async def generate(
        self,
        song: Track,
    ) -> str:

        try:
            temp = f"cache/raw_{song.id}.jpg"
            output = f"cache/{song.id}.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(
                temp,
                song.thumbnail,
            )

            img = (
                Image.open(temp)
                .convert("RGBA")
            )

            bg = img.resize(
                (
                    self.width,
                    self.height,
                ),
                Image.Resampling.LANCZOS,
            )

            bg = bg.filter(
                ImageFilter.GaussianBlur(40)
            )

            bg = ImageEnhance.Brightness(
                bg
            ).enhance(0.40)

            draw = ImageDraw.Draw(bg)

            frame_x = 100
            frame_y = (
                self.height
                - self.album_size
            ) // 2
            album = img.resize(
                (
                    self.album_size,
                    self.album_size,
                ),
                Image.Resampling.LANCZOS,
            )

            mask = Image.new(
                "L",
                (
                    self.album_size,
                    self.album_size,
                ),
                0,
            )

            ImageDraw.Draw(mask).rounded_rectangle(
                (
                    0,
                    0,
                    self.album_size,
                    self.album_size,
                ),
                radius=self.radius,
                fill=255,
            )

            shadow = Image.new(
                "RGBA",
                (
                    self.album_size + 40,
                    self.album_size + 40,
                ),
                (0, 0, 0, 0),
            )

            ImageDraw.Draw(shadow).rounded_rectangle(
                (
                    20,
                    20,
                    self.album_size + 20,
                    self.album_size + 20,
                ),
                radius=self.radius,
                fill=(0, 0, 0, 170),
            )

            shadow = shadow.filter(
                ImageFilter.GaussianBlur(18)
            )

            bg.paste(
                shadow,
                (
                    frame_x - 20,
                    frame_y - 20,
                ),
                shadow,
            )

            bg.paste(
                album,
                (
                    frame_x,
                    frame_y,
                ),
                mask,
            )

            draw.rounded_rectangle(
                (
                    frame_x,
                    frame_y,
                    frame_x + self.album_size,
                    frame_y + self.album_size,
                ),
                radius=self.radius,
                outline=(255, 255, 255, 90),
                width=5,
            )

            text_x = 620

            glass = Image.new(
                "RGBA",
                (
                    self.width,
                    self.height,
                ),
                (0, 0, 0, 0),
            )

            glass_draw = ImageDraw.Draw(glass)

            glass_draw.rounded_rectangle(
                (
                    text_x - 40,
                    frame_y,
                    self.width - 60,
                    frame_y + self.album_size,
                ),
                radius=35,
                fill=(255, 255, 255, 25),
            )

            bg.alpha_composite(glass)

            title = self.trim_text(
                song.title,
                self.font_title,
                560,
            )

            artist = self.trim_text(
                song.channel_name,
                self.font_artist,
                500,
            )

            draw.text(
                (
                    text_x,
                    frame_y + 40,
                ),
                title,
                font=self.font_title,
                fill=(255, 255, 255),
            )

            draw.text(
                (
                    text_x,
                    frame_y + 120,
                ),
                f"By {artist}",
                font=self.font_artist,
                fill=(220, 220, 220),
            )

            draw.text(
                (
                    text_x,
                    frame_y + 185,
                ),
                f"Views : {song.view_count}",
                font=self.font_small,
                fill=(180, 180, 180),
            )
            # Progress Bar
            bar_x = text_x
            bar_y = frame_y + 320
            bar_width = 500
            bar_height = 8

            draw.rounded_rectangle(
                (
                    bar_x,
                    bar_y,
                    bar_x + bar_width,
                    bar_y + bar_height,
                ),
                radius=5,
                fill=(255, 255, 255, 50),
            )

            progress = 0.40

            draw.rounded_rectangle(
                (
                    bar_x,
                    bar_y,
                    bar_x + (bar_width * progress),
                    bar_y + bar_height,
                ),
                radius=5,
                fill=(0, 200, 255, 255),
            )

            circle = 10

            draw.ellipse(
                (
                    bar_x + (bar_width * progress) - circle,
                    bar_y - 6,
                    bar_x + (bar_width * progress) + circle,
                    bar_y + 14,
                ),
                fill=(255, 255, 255),
            )

            draw.text(
                (
                    bar_x,
                    bar_y + 25,
                ),
                "00:01",
                font=self.font_small,
                fill=(255, 255, 255),
            )

            draw.text(
                (
                    bar_x + bar_width - 80,
                    bar_y + 25,
                ),
                song.duration,
                font=self.font_small,
                fill=(255, 255, 255),
            )

            bg = bg.convert("RGB")

            bg.save(
                output,
                quality=95,
            )

            try:
                os.remove(temp)
            except Exception:
                pass

            return output

        except Exception as e:
            import traceback
            print(f"[Thumbnail Error] {e}")
            traceback.print_exc()
            return config.DEFAULT_THUMB
