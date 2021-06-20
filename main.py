# https://8mb.video/
# https://github.com/kkroening/ffmpeg-python
# https://github.com/Czechball/discord-video/blob/main/discord-video.sh
# https://kkroening.github.io/ffmpeg-python/#ffmpeg.probe

from os import remove
from tempfile import NamedTemporaryFile
import ffmpeg
from flask import Flask, render_template, request, abort


app = Flask('app')

# 64 000 000 bits / video length = target bitrate
MAX_VIDEO_SIZE = 60_000_000
MAX_AUDIO_SIZE = 4_000_000

# Command explained == ffmpeg -hide_banner -i "$1" -c:v libvpx-vp9 -b:v "$VIDEO_BITRATE" -vf scale=1280:720 -c:a libopus -b:a "$AUDIO_BITRATE" "$1-compressed.webm":
# hide banner
# input
# change video codec to libvpx-vp9 (codec for WebM)
# change video bitrate
# scale resolution to 720p
# change audio codec to Opus
# change audio bitrate
# convert to WebM

@app.route('/')
def index():
	return render_template("index.html")


@app.route('/run', methods=["POST"])
def run():
	_file = request.files.get("file")
	if not _file:
		abort(400)

	with NamedTemporaryFile(delete=False) as file:
		file.write(_file.read())
		filename = file.name

		try:
			info = ffmpeg.probe(filename)
		except ffmpeg.Error as e:
			return f"""Error:
		<pre>{e.stderr.decode('utf-8')}</pre>""", 500

		duration = int(float(info["format"]["duration"]))
		video_bitrate = MAX_VIDEO_SIZE / duration * 60 / 100
		audio_bitrate = MAX_AUDIO_SIZE / duration * 75 / 100

		# format = info["format"]["format_name"]
		vcodec = [s for s in info["streams"]
					if s["codec_type"] == "video"][0].get("codec_name")
		acodec = [s for s in info["streams"]
					if s["codec_type"] == "audio"][0].get("codec_name")

		try:
			process = (
				ffmpeg
				.input(filename, vcodec=vcodec, acodec=acodec)
				.filter("scale", 1280, 720)
				.output(
					"pipe:",
					acodec="opus",
					vcodec="libvpx-vp9",
					format="webm",
					video_bitrate=video_bitrate,
					audio_bitrate=audio_bitrate,
				)
				.run_async(pipe_stdout=True)
			)
		except ffmpeg.Error as e:
			return f"Error: <pre>{e.stderr.decode('utf-8')}</pre>", 500
		else:
			def generate():
				for line in process.stdout:
					yield line
				remove(file.name)
			return app.response_class(generate(), mimetype='video/webm')
			


app.run(host='0.0.0.0', port=8080)
