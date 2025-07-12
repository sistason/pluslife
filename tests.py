import os
import re
import sys
import json
import datetime

from pluslife import PluslifeTestrun, get_plotimage_from_data

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        pluslife_test_data = json.load(f)

    # filename is expected to contain ISO-Time ("2025-01-01T...Z"), default is "pluslife_test_data-${ISOdate}.json"
    time_string = re.search(r"(?P<time>\d\d\d\d-\d\d-\d\d.+?)\.", os.path.basename(sys.argv[1]).removesuffix(".json"))

    testrun = PluslifeTestrun(
        pluslife_test_data, start=datetime.datetime.strptime(time_string.group("time"), "%Y-%m-%dT%H_%M_%S")
    )
    with open(sys.argv[1] + ".tested", "w") as f:
        json.dump(testrun.to_json(), f)

    assert testrun.to_json() == pluslife_test_data
    assert testrun.start is not None
    assert (datetime.datetime.now() - testrun.start).seconds > 300  # testrun.start is not "now()"

    get_plotimage_from_data(testrun).save("current_plot.png")
