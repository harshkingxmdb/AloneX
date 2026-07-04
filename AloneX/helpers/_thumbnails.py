import os
import math
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

        self.album_size = 520
        self.radius = 36

        self.font_title = ImageFont.truetype(
            "AloneX/helpers/Raleway-Bold.ttf",
            36,
        )

        self.font_artist = ImageFont.truetype(
            "AloneX/helpers/Inter-Light.ttf",
            26,
        )

        self.font_small = ImageFont.truetype(
            "AloneX/helpers/Inter-Light.ttf",
            22,
        )

    # ---------------- basic helpers ----------------

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

    # ---------------- icon drawing helpers ----------------

    def draw_icon_bg(self, draw, center, radius, fill=(255, 255, 255, 60)):
        x, y = center
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=fill,
        )

    def draw_star(self, draw, center, size, color=(255, 255, 255, 255)):
        x, y = center
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = size if i % 2 == 0 else size * 0.42
            points.append(
                (x + r * math.cos(angle), y - r * math.sin(angle))
            )
        draw.polygon(points, outline=color, width=2)

    def draw_dots_menu(self, draw, center, size, color=(120, 120, 120, 255)):
        x, y = center
        r = size * 0.11
        for i in (-1, 0, 1):
            cy = y + i * size * 0.34
            draw.ellipse([x - r, cy - r, x + r, cy + r], fill=color)

    def draw_circle_button(self, draw, center, radius, filled=True):
        x, y = center
        bbox = [x - radius, y - radius, x + radius, y + radius]
        if filled:
            draw.ellipse(bbox, fill=(255, 255, 255, 255))
        else:
            draw.ellipse(bbox, outline=(255, 255, 255, 180), width=3)

    def draw_pause_bars(self, draw, center, size, color=(35, 25, 20, 255)):
        x, y = center
        bar_w = size * 0.17
        bar_h = size * 0.9
        gap = size * 0.20
        draw.rounded_rectangle(
            [x - gap - bar_w / 2, y - bar_h / 2, x - gap + bar_w / 2, y + bar_h / 2],
            radius=2,
            fill=color,
        )
        draw.rounded_rectangle(
            [x + gap - bar_w / 2, y - bar_h / 2, x + gap + bar_w / 2, y + bar_h / 2],
            radius=2,
            fill=color,
        )

    def draw_skip_icon(self, draw, center, size, forward=True, color=(255, 255, 255, 255)):
        x, y = center
        tri_w = size * 0.44
        tri_h = size * 0.95
        gap = size * 0.26
        for dx in (-gap, gap):
            cx = x + dx
            if forward:
                pts = [
                    (cx - tri_w / 2, y - tri_h / 2),
                    (cx - tri_w / 2, y + tri_h / 2),
                    (cx + tri_w / 2, y),
                ]
            else:
                pts = [
                    (cx + tri_w / 2, y - tri_h / 2),
                    (cx + tri_w / 2, y + tri_h / 2),
                    (cx - tri_w / 2, y),
                ]
            draw.polygon(pts, fill=color)

    def draw_speaker(self, draw, pos, size, color=(255, 255, 255, 255), loud=True):
        x, y = pos
        body_w = size * 0.36
        body_h = size * 0.5
        draw.polygon(
            [
                (x, y - body_h * 0.22),
                (x + body_w * 0.42, y - body_h * 0.22),
                (x + body_w, y - body_h / 2),
                (x + body_w, y + body_h / 2),
                (x + body_w * 0.42, y + body_h * 0.22),
                (x, y + body_h * 0.22),
            ],
            fill=color,
        )
        if loud:
            draw.arc(
                [x + body_w - 2, y - size * 0.38, x + body_w + size * 0.38, y + size * 0.38],
                -55, 55, fill=color, width=3,
            )
            draw.arc(
                [x + body_w - 2, y - size * 0.22, x + body_w + size * 0.22, y + size * 0.22],
                -55, 55, fill=color, width=3,
            )

    def draw_quote_bubble(self, draw, center, size, color=(255, 255, 255, 255)):
        x, y = center
        top = y - size * 0.42
        bottom = y + size * 0.10
        draw.rounded_rectangle(
            [x - size / 2, top, x + size / 2, bottom],
            radius=size * 0.22,
            outline=color,
            width=3,
        )
        draw.polygon(
            [
                (x - size * 0.14, bottom - 2),
                (x - size * 0.14, bottom + size * 0.24),
                (x + size * 0.12, bottom - 2),
            ],
            fill=color,
        )
        qh = size * 0.16
        qw = size * 0.09
        cy = (top + bottom) / 2 - 2
        draw.rounded_rectangle(
            [x - size * 0.20, cy - qh / 2, x - size * 0.20 + qw, cy + qh / 2],
            radius=2, fill=color,
        )
        draw.rounded_rectangle(
            [x + size * 0.06, cy - qh / 2, x + size * 0.06 + qw, cy + qh / 2],
            radius=2, fill=color,
        )

    def draw_list_icon(self, draw, center, size, color=(255, 255, 255, 255)):
        x, y = center
        line_w = size * 0.62
        for dy in (-size * 0.28, 0, size * 0.28):
            r = size * 0.05
            draw.ellipse(
                [x - line_w / 2 - r * 2, y + dy - r, x - line_w / 2, y + dy + r],
                fill=color,
            )
            draw.line(
                [(x - line_w / 2 + size * 0.14, y + dy), (x + line_w / 2, y + dy)],
                fill=color, width=4,
            )

    # ---------------- main generator ----------------

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

            img = Image.open(temp).convert("RGBA")

            bg = img.resize(
                (self.width, self.height),
                Image.Resampling.LANCZOS,
            )
            bg = bg.filter(ImageFilter.GaussianBlur(45))
            bg = ImageEnhance.Brightness(bg).enhance(0.32)
            bg = bg.convert("RGBA")

            overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # ---------- album art (left) ----------
            frame_x = 90
            frame_y = (self.height - self.album_size) // 2

            album = img.resize(
                (self.album_size, self.album_size),
                Image.Resampling.LANCZOS,
            )

            mask = Image.new("L", (self.album_size, self.album_size), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, self.album_size, self.album_size),
                radius=self.radius,
                fill=255,
            )

            shadow = Image.new(
                "RGBA",
                (self.album_size + 40, self.album_size + 40),
                (0, 0, 0, 0),
            )
            ImageDraw.Draw(shadow).rounded_rectangle(
                (20, 20, self.album_size + 20, self.album_size + 20),
                radius=self.radius,
                fill=(0, 0, 0, 170),
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(18))

            bg.alpha_composite(shadow, (frame_x - 20, frame_y - 20))
            bg.paste(album, (frame_x, frame_y), mask)

            # ---------- right column ----------
            text_x = 716
            right_edge = 1160
            top_y = 118

            title = self.trim_text(song.title, self.font_title, 330)
            artist = self.trim_text(song.channel_name, self.font_artist, 350)

            draw.text((text_x, top_y), title, font=self.font_title, fill=(255, 255, 255, 255))
            draw.text(
                (text_x, top_y + 50),
                artist,
                font=self.font_artist,
                fill=(200, 200, 200, 255),
            )

            # star + menu dots (top right) with gray circle backgrounds
            star_c = (1068, 145)
            dots_c = (1141, 145)
            self.draw_icon_bg(draw, star_c, 26, fill=(210, 210, 210, 130))
            self.draw_star(draw, star_c, 12, color=(255, 255, 255, 255))
            self.draw_icon_bg(draw, dots_c, 26, fill=(230, 230, 230, 160))
            self.draw_dots_menu(draw, dots_c, 26, color=(120, 120, 120, 255))

            # ---------- progress bar ----------
            bar_y = 224
            bar_x = text_x
            bar_width = right_edge - text_x
            bar_height = 8

            draw.rounded_rectangle(
                (bar_x, bar_y - bar_height / 2, bar_x + bar_width, bar_y + bar_height / 2),
                radius=4,
                fill=(255, 255, 255, 150),
            )

            progress = 0.02
            handle_r = 8
            hx = bar_x + bar_width * progress
            draw.ellipse(
                (hx - handle_r, bar_y - handle_r, hx + handle_r, bar_y + handle_r),
                fill=(255, 255, 255, 255),
            )

            draw.text(
                (bar_x, bar_y + 20),
                "0:03",
                font=self.font_small,
                fill=(210, 210, 210, 255),
            )
            duration_text = f"-{song.duration}"
            dur_w = self.font_small.getlength(duration_text)
            draw.text(
                (bar_x + bar_width - dur_w, bar_y + 20),
                duration_text,
                font=self.font_small,
                fill=(210, 210, 210, 255),
            )

            # ---------- playback controls ----------
            controls_y = 380
            center_x = 939

            rewind_c = (center_x - 159, controls_y)
            play_c = (center_x, controls_y)
            forward_c = (center_x + 159, controls_y)

            self.draw_skip_icon(draw, rewind_c, 62, forward=False)
            self.draw_circle_button(draw, play_c, 29, filled=True)
            self.draw_pause_bars(draw, play_c, 30)
            self.draw_skip_icon(draw, forward_c, 62, forward=True)

            # ---------- volume row ----------
            vol_y = 498
            self.draw_speaker(draw, (bar_x, vol_y), 28, loud=False)

            vol_bar_x1 = bar_x + 55
            vol_bar_x2 = right_edge - 55
            draw.rounded_rectangle(
                (vol_bar_x1, vol_y - 5, vol_bar_x2, vol_y + 5),
                radius=5,
                fill=(255, 255, 255, 235),
            )
            self.draw_speaker(draw, (right_edge - 28, vol_y), 28, loud=True)

            # ---------- bottom icons ----------
            icons_y = 582
            self.draw_quote_bubble(draw, (835, icons_y), 36)
            self.draw_list_icon(draw, (1042, icons_y), 36)

            bg = Image.alpha_composite(bg, overlay)
            bg = bg.convert("RGB")

            bg.save(output, quality=95)

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