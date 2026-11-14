import unittest
import xml.etree.ElementTree as ET
from render import render, sample, NS, WIDTH, HEIGHT, LEFT, RIGHT, calendar_data

N="{"+NS+"}"
def fixture(empty=False):
    c=sample()
    for w in c["weeks"]:
        for d in w["contributionDays"]: d.update(contributionCount=0,contributionLevel="NONE")
    if not empty:
        c["weeks"][0]["contributionDays"][0].update(contributionCount=4,contributionLevel="SECOND_QUARTILE")
        c["weeks"][-1]["contributionDays"][6].update(contributionCount=9,contributionLevel="FOURTH_QUARTILE")
    return c

class OriginalTests(unittest.TestCase):
    def test_continuous_motion(self):
        root=ET.fromstring(render(fixture()))
        track=root.find(f".//{N}g[@id='player-ship']/{N}animateTransform")
        self.assertEqual(track.attrib["values"],f"{LEFT} 0;{RIGHT} 0;{LEFT} 0")
        self.assertAlmostEqual(float(track.attrib["dur"][:-1]),2*(RIGHT-LEFT)/220,places=5)
        self.assertEqual(track.attrib["calcMode"],"linear")
    def test_timing(self):
        for a in ET.fromstring(render(fixture())).iter():
            if a.tag not in (N+"animate",N+"animateTransform"): continue
            t=list(map(float,a.attrib["keyTimes"].split(";")))
            self.assertEqual((t[0],t[-1]),(0,1))
            self.assertTrue(all(x<y for x,y in zip(t,t[1:])))
            self.assertEqual(len(t),len(a.attrib["values"].split(";")))
    def test_real_counts(self):
        s=render(fixture())
        self.assertIn("2 ACTIVE DAYS / 13 CONTRIBUTIONS",s)
        self.assertIn("SCORE 0013",s)
    def test_empty(self):
        s=render(fixture(True))
        self.assertIn("0 ACTIVE DAYS / 0 CONTRIBUTIONS",s)
        self.assertIn("SCORE 0000",s)
    def test_dense(self):
        c=sample()
        for w in c["weeks"]:
            for d in w["contributionDays"]: d.update(contributionCount=1,contributionLevel="FIRST_QUARTILE")
        s=render(c)
        self.assertIn("364 ACTIVE DAYS / 364 CONTRIBUTIONS",s)
        self.assertIn("SCORE 0364",s)
    def test_layout_and_speed(self):
        root=ET.fromstring(render(fixture(),220))
        self.assertEqual(root.attrib["viewBox"],f"0 0 {WIDTH} {HEIGHT}")
        self.assertEqual(len(root.findall(f".//{N}path[@id='calendar-grid']")),1)
        for speed in (0,301,float("nan")):
            with self.assertRaises(ValueError): render(fixture(),speed)
    def test_visual_identity(self):
        root=ET.fromstring(render(fixture()))
        self.assertIsNotNone(root.find(f".//{N}path[@id='fighter-hull']"))
        self.assertIsNotNone(root.find(f".//{N}path[@id='mono-emblem']"))
        self.assertIsNotNone(root.find(f".//{N}path[@id='retro-title']"))
        self.assertIsNotNone(root.find(f".//{N}path[@id='retro-landscape']"))
        ship=root.find(f".//{N}g[@id='player-ship']")
        self.assertEqual(len(list(ship.iter(N+"animateTransform"))),1)
        self.assertEqual(len(list(ship.iter(N+"animate"))),0)
        self.assertNotIn("BY MATHEUS",ET.tostring(root,encoding="unicode"))
        self.assertIsNotNone(root.find(f".//{N}g[@id='activity-legend']"))
    def test_combat_refinement(self):
        root=ET.fromstring(render(fixture()))
        enemies=[p for p in root.iter(N+"path") if p.get("id","").startswith("enemy-")]
        self.assertEqual(len(enemies),2)
        self.assertTrue(all(p.get("d","").count("h1v1h-1z")>20 for p in enemies))
        tracks=[a for a in root.iter(N+"animate") if a.get("values")=="0;0;1;0;0"]
        self.assertEqual(len(tracks),2)
        ship=root.find(f".//{N}g[@id='player-ship']")
        self.assertEqual(len(list(ship.iter(N+"animateTransform"))),1)
    def test_no_external_resources(self):
        s=render(fixture())
        self.assertNotIn("href=",s)
        self.assertNotIn("<script",s)
        self.assertNotIn("gh-space-shooter",s)

if __name__=="__main__": unittest.main()
