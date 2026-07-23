import os
import tempfile
import unittest

from ip2region_xdb.converter import MMDBConverter


class ParseGeoLiteRecordTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        with open(
            os.path.join(self.temp_dir.name, "countries.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("US,美国\nTR,土尔其\nHK,香港(中国)\n")
        with open(
            os.path.join(self.temp_dir.name, "us_states.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("俄勒冈州,Oregon\n")
        self.converter = MMDBConverter(
            "city.mmdb",
            "country.mmdb",
            "asn.mmdb",
            data_dir=self.temp_dir.name,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_country_name_uses_iso_code_mapping(self):
        data = {
            "country": {
                "iso_code": "TR",
                "names": {"zh-CN": "土耳其", "en": "Türkiye"},
            },
        }

        self.assertEqual("土尔其", self.converter._parse_city_record(data)["country"])
        self.assertEqual(("", "土尔其"), self.converter._parse_country_record(data))

    def test_unconfigured_country_falls_back_to_geolite_name(self):
        data = {
            "country": {
                "iso_code": "BQ",
                "names": {
                    "zh-CN": "博奈尔岛、圣尤斯达蒂斯和萨巴",
                    "en": "Bonaire, Sint Eustatius and Saba",
                },
            },
        }

        parsed = self.converter._parse_city_record(data)
        self.assertEqual("博奈尔岛、圣尤斯达蒂斯和萨巴", parsed["country"])

    def test_us_state_uses_configured_chinese_name(self):
        data = {
            "country": {
                "iso_code": "US",
                "names": {"zh-CN": "美国", "en": "United States"},
            },
            "subdivisions": [{
                "iso_code": "OR",
                "names": {"zh-CN": "GeoLite中文名", "en": "Oregon"},
            }],
        }

        parsed = self.converter._parse_city_record(data)
        self.assertEqual("美国", parsed["country"])
        self.assertEqual("俄勒冈州", parsed["province"])


if __name__ == "__main__":
    unittest.main()
