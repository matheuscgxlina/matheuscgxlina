import copy
import unittest
import xml.etree.ElementTree as ET
from generate_invaders import render, sample, NS, parse

class GeneratorTests(unittest.TestCase):
    def test_demo_is_labelled(self):
        out=render(sample(),demo=True)
        self.assertIn('DEMO / SAMPLE DATA',out)
        self.assertIn('animateTransform',out)
        ET.fromstring(out)
    def test_empty_activity(self):
        cal=sample()
        for week in cal['weeks']:
            for d in week['contributionDays']:
                d['contributionCount']=0; d['contributionLevel']='NONE'
        out=render(cal)
        self.assertIn('0 ACTIVE DAYS  /  0 CONTRIBUTIONS',out)
        self.assertNotIn('animateTransform',out)
    def test_two_days(self):
        cal=sample(); days=[d for w in cal['weeks'] for d in w['contributionDays']]
        for d in days: d['contributionCount']=0; d['contributionLevel']='NONE'
        for i,n in [(3,2),(360,8)]:
            days[i]['contributionCount']=n; days[i]['contributionLevel']='FIRST_QUARTILE'
        out=render(cal)
        self.assertIn('2 ACTIVE DAYS  /  10 CONTRIBUTIONS',out)
        self.assertIn('SCORE 0010',out)
        self.assertNotIn('DEMO / SAMPLE DATA',out)
    def test_dense_and_timing(self):
        cal=sample()
        for week in cal['weeks']:
            for d in week['contributionDays']:
                d['contributionCount']=3; d['contributionLevel']='FOURTH_QUARTILE'
        root=ET.fromstring(render(cal))
        for a in root.iter():
            if a.tag in ('{'+NS+'}animate','{'+NS+'}animateTransform'):
                times=list(map(float,a.attrib['keyTimes'].split(';')))
                self.assertEqual(len(times),len(a.attrib['values'].split(';')))
                self.assertEqual(times[0],0); self.assertEqual(times[-1],1)
                self.assertTrue(all(x<y for x,y in zip(times,times[1:])))
        self.assertIn('SCORE 1092',ET.tostring(root,encoding='unicode'))
    def test_invalid_calendar(self):
        cal=sample(); cal['weeks'][0]['contributionDays'][0]['weekday']=9
        with self.assertRaises(ValueError): parse(cal)
    def test_deterministic(self):
        self.assertEqual(render(sample()),render(copy.deepcopy(sample())))

if __name__=='__main__': unittest.main()
