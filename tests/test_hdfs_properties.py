"""Regression for Hadoop VERSION comments; never creates dataset/HDFS evidence."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hdfs_restart_verify import properties

class StoragePropertiesTests(unittest.TestCase):
    def test_timestamp_comment_is_not_storage_identity(self):
        before='#Mon Oct 12 07:25:13 UTC 2026\nclusterID=hdfs-demo\nstorageID=DS-demo\nlayoutVersion=-57\n'
        after='#Mon Oct 12 07:45:31 UTC 2026\nlayoutVersion=-57\nstorageID=DS-demo\nclusterID=hdfs-demo\n'
        self.assertEqual(properties(before),properties(after))

    def test_any_storage_property_change_is_detected(self):
        original='clusterID=hdfs-demo\nstorageID=DS-demo\nlayoutVersion=-57\n'
        for changed in ['clusterID=foreign','storageID=DS-foreign','layoutVersion=-58']:
            key=changed.split('=')[0]
            rows=[row for row in original.splitlines() if not row.startswith(key+'=')]
            self.assertNotEqual(properties(original),properties('\n'.join(rows+[changed])))

    def test_duplicate_storage_property_is_rejected(self):
        with self.assertRaises(ValueError):properties('clusterID=a\nclusterID=b\n')

if __name__=='__main__':unittest.main()
