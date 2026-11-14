#!/usr/bin/env python3
"""MONO / INVADERS — REMAKE; theme for the pinned MIT gh-space-shooter engine."""
import argparse
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".remake-upstream" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import gh_space_shooter.constants as constants
# GitHub's rolling calendar normally includes 53 weeks, including partial weeks.
constants.NUM_WEEKS = 53
from gh_space_shooter.game import animator as engine
from gh_space_shooter.game.renderer import Renderer
from gh_space_shooter.game.render_context import RenderContext
from gh_space_shooter.game.strategies.column_strategy import ColumnStrategy
from gh_space_shooter.output.webp_provider import WebPOutputProvider
from generate_invaders import get_calendar, parse, sample

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
MONTHS = []
TOTAL = 0
ACTIVE = 0
FPS = 80  # Upstream writes 2000/FPS ms per frame: 80 yields actual 40 fps.

def theme():
    return RenderContext(
        cell_size=12, cell_spacing=3, padding=40,
        background_color=(16,16,16), grid_color=(38,38,38),
        enemy_colors={1:(102,102,102),2:(153,153,153),3:(192,192,192),4:(241,241,241)},
        ship_color=(237,237,237), bullet_color=(255,255,255))

RenderContext.darkmode = staticmethod(theme)

class MonoRenderer(Renderer):
    """Only drawing is customized. Upstream game state and timing are unchanged."""
    def render_frame(self):
        img = Image.new("RGB", (self.width, self.height), self.context.background_color)
        overlay = Image.new("RGBA", img.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        for col in range(constants.NUM_WEEKS):
            for row in range(constants.NUM_DAYS):
                x,y = self.context.get_cell_position(col,row)
                size = self.context.cell_size
                draw.rounded_rectangle((x,y,x+size,y+size),radius=2,fill=self.context.grid_color)
        self.game_state.draw(draw,self.context)
        try:
            font = ImageFont.truetype("DejaVuSansMono.ttf",15)
            small = ImageFont.truetype("DejaVuSansMono.ttf",10)
        except OSError:
            font = small = ImageFont.load_default()
        draw.rectangle((0,0,self.width,30),fill=self.context.background_color)
        draw.text((20,9),"MONO / INVADERS — REMAKE",font=font,fill=(237,237,237))
        draw.text((self.width-20,11),"CONTRIBUTION ARCADE",font=small,fill=(153,153,153),anchor="ra")
        draw.line((20,31,self.width-20,31),fill=(59,59,59))
        for col, month in MONTHS:
            x,_ = self.context.get_cell_position(col,0)
            draw.text((x,32),month,font=small,fill=(153,153,153),anchor="ls")
        footer_y=self.height-18
        draw.rectangle((0,footer_y,self.width,self.height),fill=self.context.background_color)
        draw.line((20,footer_y,self.width-20,footer_y),fill=(59,59,59))
        draw.text((20,footer_y+4),"POWERED BY GH-SPACE-SHOOTER",font=small,fill=(153,153,153))
        draw.text((self.width-20,footer_y+4),f"{ACTIVE} ACTIVE DAYS / {TOTAL} CONTRIBUTIONS",font=small,fill=(153,153,153),anchor="ra")
        return Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")

engine.Renderer = MonoRenderer

def adapt(calendar):
    global TOTAL, ACTIVE, MONTHS
    days,ncols = parse(calendar)
    start=max(0,ncols-constants.NUM_WEEKS)
    offset=max(0,constants.NUM_WEEKS-ncols)
    weeks=[{"days":[{"date":"","count":0,"level":0} for _ in range(7)]}
           for _ in range(constants.NUM_WEEKS)]
    MONTHS=[]; last_month=None; last_col=-10
    for col,row,date,count,level in days:
        if col<start: continue
        x=col-start+offset
        weeks[x]["days"][row]={"date":str(date),"count":count,"level":LEVELS[level]}
        key=(date.year,date.month)
        if key!=last_month and x-last_col>=2:
            MONTHS.append((x,date.strftime("%b").upper()))
            last_month=key; last_col=x
    TOTAL=sum(d["count"] for w in weeks for d in w["days"])
    ACTIVE=sum(d["count"]>0 for w in weeks for d in w["days"])
    return {"username":"matheuscgxlina","total_contributions":TOTAL,"weeks":weeks}

def render(calendar, output):
    data=adapt(calendar)
    animator=engine.Animator(data,ColumnStrategy(),fps=FPS)
    def bounded():
        for i,frame in enumerate(animator.generate_frames()):
            if i>=4000: raise RuntimeError("Animation exceeds safe frame budget")
            yield frame
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        target=Path(directory)/"remake.webp"
        provider=WebPOutputProvider(str(target))
        provider.write(provider.encode(bounded(),animator.frame_duration))
        with Image.open(target) as im:
            if not im.is_animated or im.info.get("loop")!=0 or im.n_frames<2:
                raise ValueError("Invalid animated WebP")
            elapsed=0
            for i in range(im.n_frames):
                im.seek(i); im.load(); elapsed+=im.info.get("duration",0)
            print(f"Verified {im.n_frames} frames; {elapsed} ms; {im.size}; {TOTAL} contributions")
        target.replace(output)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:
        cal=sample()
        for week in cal["weeks"]:
            for day in week["contributionDays"]:
                day.update(contributionCount=0,contributionLevel="NONE")
        cal["weeks"][-1]["contributionDays"][3].update(contributionCount=5,contributionLevel="FOURTH_QUARTILE")
    else:
        cal=get_calendar("matheuscgxlina")
    render(cal,args.output)
