import matplotlib
from scipy.interpolate import interp1d

matplotlib.use("agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from .models import PluslifeTestrun

CHANNEL_COLORS = ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f"]


def _testrun_to_nparrays(testrun: PluslifeTestrun, normalize=False):
    channels = {}
    for sample in testrun.samples:
        if sample.startingChannel not in channels:
            channels[sample.startingChannel] = (np.array([]), np.array([]))
        channels[sample.startingChannel] = (
            np.append(channels[sample.startingChannel][0], sample.samplingTime / 60.0 / 10.0),
            np.append(channels[sample.startingChannel][1], sample.firstChannelResult),
        )

    smoothed_data = {}
    for channel, (times, values) in channels.items():
        if normalize:
            if len(values) > 2:
                initial_value = (values[0] + values[1] + values[2]) / 3
            elif len(values) > 1:
                initial_value = (values[0] + values[1]) / 2
            else:
                initial_value = values[0]
            values = [y - initial_value for y in values]

        try:
            spline = interp1d(times, values, kind="cubic")
            splined_times = np.linspace(times.min(), times.max(), 500)
            smoothed_data[channel] = [splined_times, spline(splined_times)]
        except ValueError:
            smoothed_data[channel] = [times, values]

    return smoothed_data


def get_plotimage_from_data(testrun, width=1920, height=1080, normalize=True) -> Image:
    arrays = _testrun_to_nparrays(testrun, normalize=normalize)

    fig, ax = plt.subplots(figsize=(width / 100.0, height / 100.0))
    for channel, (x, y) in arrays.items():
        ax.plot(x, y, color=CHANNEL_COLORS[int(channel)], label=f"Channel {channel}")

    ax.legend(loc="upper left", shadow=True, fontsize="large")
    ax.set_title(f"Pluslife Test of {testrun.testType.name} at {testrun.start}")
    ax.set_xlabel("Time [min]")
    ax.margins(0, 0.1)

    fig.canvas.draw()
    img = Image.frombytes("RGBa", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")

    return img
