import unittest
import xml.etree.ElementTree as ET
from render import (render, sample, NS, WIDTH, HEIGHT, LEFT, RIGHT, GRID_X,
                    STEP, CELL, DEFAULT_SPEED, MAX_BYTES, COLORS, calendar_data)

N="{"+NS+"}"
def fixture(empty=False,dense=False):
    c=sample()
    for w in c["weeks"]:
        for d in w["contributionDays"]:
            d.update(contributionCount=1 if dense else 0,
                     contributionLevel="FIRST_QUARTILE" if dense else "NONE")
    if not empty and not dense:
        c["weeks"][0]["contributionDays"][0].update(contributionCount=4,contributionLevel="SECOND_QUARTILE")
        c["weeks"][-1]["contributionDays"][6].update(contributionCount=9,contributionLevel="FOURTH_QUARTILE")
    return c

def find(root,tag,id):
    return root.find(f".//{N}{tag}[@id='{id}']")

class OriginalTests(unittest.TestCase):
    def test_continuous_motion(self):
        root=ET.fromstring(render(fixture()))
        track=find(root,"g","player-ship").find(N+"animateTransform")
        self.assertEqual(track.get("values"),f"{LEFT} 0;{RIGHT} 0;{LEFT} 0")
        self.assertAlmostEqual(float(track.get("dur")[:-1]),2*(RIGHT-LEFT)/DEFAULT_SPEED,places=5)
        self.assertTrue(10<=float(track.get("dur")[:-1])<=15)
        self.assertEqual(track.get("calcMode"),"linear")
    def test_timing(self):
        for cal in (fixture(),fixture(True),fixture(dense=True)):
            for a in ET.fromstring(render(cal)).iter():
                if a.tag not in (N+"animate",N+"animateTransform"): continue
                t=list(map(float,a.get("keyTimes").split(";")))
                self.assertEqual((t[0],t[-1]),(0,1))
                self.assertTrue(all(x<y for x,y in zip(t,t[1:])))
                self.assertEqual(len(t),len(a.get("values").split(";")))
    def test_real_counts(self):
        root=ET.fromstring(render(fixture()))
        self.assertIn("2 ACTIVE DAYS / 13 CONTRIBUTIONS",ET.tostring(root,encoding="unicode"))
        self.assertEqual(find(root,"g","scoreboard").find(N+"title").text,"SCORE 0013")
        digit=find(root,"g","score-digit-3").find(N+"animateTransform")
        self.assertEqual(digit.get("values"),"0 0;0 -72;0 -54;0 -54")
    def test_empty(self):
        s=render(fixture(True))
        self.assertIn("0 ACTIVE DAYS / 0 CONTRIBUTIONS",s)
        self.assertIn("SCORE 0000",s)
        self.assertIn("NO ACTIVITY",s)
        self.assertNotIn('id="projectile-',s)
    def test_dense_size_and_counts(self):
        s=render(fixture(dense=True))
        self.assertIn("364 ACTIVE DAYS / 364 CONTRIBUTIONS",s)
        self.assertIn("SCORE 0364",s)
        self.assertLess(len(s.encode()),MAX_BYTES)
        print("Dense fixture SVG bytes:",len(s.encode()))
    def test_full_53_week_mixed_calendar_budget(self):
        import datetime as dt
        c=fixture(dense=True)
        start=dt.date.fromisoformat(c["weeks"][-1]["contributionDays"][-1]["date"])+dt.timedelta(days=1)
        c["weeks"].append({"contributionDays":[{"date":str(start+dt.timedelta(days=r)),
            "weekday":r,"contributionCount":1,"contributionLevel":"FIRST_QUARTILE"} for r in range(7)]})
        for col,w in enumerate(c["weeks"]):
            for row,d in enumerate(w["contributionDays"]):
                d.update(contributionCount=1+(col*37+row*19)%97,
                         contributionLevel=list(COLORS)[1+(col+row)%4])
        s=render(c); root=ET.fromstring(s)
        total=sum(d["contributionCount"] for w in c["weeks"] for d in w["contributionDays"])
        self.assertIn(f"371 ACTIVE DAYS / {total} CONTRIBUTIONS",s)
        self.assertEqual(find(root,"g","scoreboard").find(N+"title").text,f"SCORE {total:04d}")
        self.assertLess(len(s.encode()),MAX_BYTES)
        print("Full mixed 53-week SVG bytes:",len(s.encode()))
    def test_layout_and_speed(self):
        root=ET.fromstring(render(fixture()))
        self.assertEqual(root.get("viewBox"),f"0 0 {WIDTH} {HEIGHT}")
        self.assertIsNotNone(find(root,"path","calendar-grid"))
        for speed in (0,171,float("nan")):
            with self.assertRaises(ValueError): render(fixture(),speed)
    def test_visual_identity(self):
        root=ET.fromstring(render(fixture()))
        for id in ("fighter-hull","mono-emblem","retro-title","retro-landscape","retro-frame","marquee-lines"):
            self.assertIsNotNone(find(root,"path",id))
        self.assertEqual(find(root,"path","marquee-lines").get("d").count("M"),2)
        ship=find(root,"g","player-ship")
        self.assertEqual(len(list(ship.iter(N+"animateTransform"))),1)
        self.assertNotIn("Original Edition",ET.tostring(root,encoding="unicode"))
    def test_persistent_activity(self):
        root=ET.fromstring(render(fixture()))
        for lv in ("SECOND_QUARTILE","FOURTH_QUARTILE"):
            cell=find(root,"path","activity-"+lv.lower())
            self.assertEqual(cell.get("fill"),COLORS[lv])
            self.assertEqual(len(list(cell.iter(N+"animate"))),0)
        self.assertEqual(len(set(COLORS.values())),5)
        self.assertIn("PATROL MODE",ET.tostring(root,encoding="unicode"))
        self.assertIsNotNone(find(root,"g","patrol-scanner"))
    def test_combat_refinement(self):
        root=ET.fromstring(render(fixture()))
        self.assertGreater(find(root,"path","enemy-sprite").get("d").count("h1v1h-1z"),20)
        enemies=[n for n in root.iter(N+"g") if n.get("id","").startswith("enemies-")]
        self.assertEqual(sum(n.find(N+"path").get("d").count("M") for n in enemies),2)
        self.assertIsNotNone(find(root,"pattern","enemy-pattern"))
        cutters=[n for n in root.iter(N+"clipPath") if n.get("id","").startswith("cut-")]
        self.assertEqual(len(cutters),2)
        self.assertTrue(all(n.find(N+"rect").find(N+"animate") is not None for n in cutters))
    def test_visible_projectiles_and_impacts(self):
        root=ET.fromstring(render(fixture()))
        bolts=[g for g in root.iter(N+"g") if g.get("id","").startswith("projectile-")]
        impacts=[g for g in root.iter(N+"g") if g.get("id","").startswith("impact-row-")]
        self.assertTrue(bolts)
        self.assertEqual(len(impacts),2)
        for g in bolts+impacts:
            self.assertIn("1",g.find(N+"animate").get("values").split(";"))
            self.assertIsNotNone(g.find(N+"animateTransform"))
    def test_month_anchors(self):
        days=calendar_data(fixture()); months={}
        for c,r,date,count,level in sorted(days,key=lambda d:d[2]):
            months.setdefault(f"month-{date.year}-{date.month:02d}",c)
        root=ET.fromstring(render(fixture()))
        labels=[n for n in root.iter(N+"text") if n.get("id","").startswith("month-")]
        self.assertEqual(len(labels),len(months))
        for label in labels:
            self.assertEqual(float(label.get("x")),GRID_X+STEP*months[label.get("id")]+CELL/2)
    def test_reduced_motion(self):
        root=ET.fromstring(render(fixture()))
        css=root.find(N+"style").text
        self.assertIn("@media (prefers-reduced-motion: reduce)",css)
        for selector in ("#player-ship","#patrol-stars","#patrol-scanner","#scoreboard",
                         '[id^="enemies-"]','[id^="projectile-"]','[id^="impact-row-"]'):
            self.assertIn(selector,css)
        self.assertIn(".reduced-motion{display:inline}",css)
        still=find(root,"g","static-patrol")
        self.assertEqual(still.get("class"),"reduced-motion")
        self.assertFalse(any(n.tag in (N+"animate",N+"animateTransform") for n in still.iter()))
        self.assertTrue(any(n.text=="SCORE 0013" and n.get("class")=="reduced-motion"
                            for n in root.iter(N+"text")))
    def test_no_external_resources(self):
        root=ET.fromstring(render(fixture()))
        ids={n.get("id") for n in root.iter() if n.get("id")}
        for n in root.iter():
            self.assertNotEqual(n.tag,N+"script")
            if n.get("href"):
                self.assertTrue(n.get("href").startswith("#"))
                self.assertIn(n.get("href")[1:],ids)
        self.assertNotIn("gh-space-shooter",ET.tostring(root,encoding="unicode"))
    def test_all_palette_levels_and_sparse_size(self):
        c=fixture(True)
        for i,lv in enumerate(list(COLORS)[1:]):
            c["weeks"][i]["contributionDays"][0].update(contributionCount=i+1,contributionLevel=lv)
        s=render(c); root=ET.fromstring(s)
        for lv in list(COLORS)[1:]:
            self.assertEqual(find(root,"path","activity-"+lv.lower()).get("fill"),COLORS[lv])
        self.assertLess(len(s.encode()),MAX_BYTES)
        print("Sparse fixture SVG bytes:",len(s.encode()))

if __name__=="__main__": unittest.main()
