import unittest
from app.windowing import choose_area,centered_rect,absolute_geometry

class MonitorTests(unittest.TestCase):
 def test_middle_monitor_with_negative_and_reordered_origins(self):
  left=(-1920,0,0,1040,True);middle=(0,-100,1920,940,False);right=(1920,0,3840,1040,False)
  self.assertEqual(choose_area([right,left,middle]),middle)
  self.assertEqual(centered_rect(middle,1340,890),(1340,890,290,-25))
 def test_popups_follow_parent_and_single_or_dual_use_primary(self):
  a=(-1920,0,0,1040,False);b=(0,0,1920,1040,True)
  self.assertEqual(choose_area([a,b]),b);self.assertEqual(choose_area([a,b],(-900,500)),a)
  self.assertEqual(choose_area([b]),b)
  self.assertEqual(centered_rect(a,2500,2000),(1920,1040,-1920,0))
 def test_absolute_offsets_support_monitors_left_and_above_primary(self):
  self.assertEqual(absolute_geometry(840,540,-1500,-20),'840x540+-1500+-20')
