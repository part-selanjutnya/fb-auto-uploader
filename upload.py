import os
import json
import requests

# File konfigurasi
LINKS_FILE = "links.txt"
FB_PAGES_DATA = os.environ.get("FB_PAGES_DATA")

DEFAULT_CAPTION = """https://part-selanjutnya.github.io/part-selanjutnya/
Tonton selanjutnya☝️
#AlurCeritaFilm #ShortMovie #FilmPendek #CeritaSeru #DramaReels #CuplikanFilm #SinopsisFilm #RekomendasiFilm #FacebookReels #ReelsViral #FYPReels #ReelsIndonesia #VideoViral #TrendingReels"""

def download_video_via_api(url, output_path="temp_video.mp4"):
    print(f"Mengunduh video dari: {url}")
    
    # 1. Coba Menggunakan API Cobalt v10 / Instance Publik Terbaru
    try:
        api_url = "https://co.wuk.sh/api/json"  # Instance resmi Cobalt v10
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "vQuality": "720"
        }
        res = requests.post(api_url, json=payload, headers=headers, timeout=20)
        data = res.json()
        
        dl_url = data.get("url") or (data.get("picker")[0]["url"] if "picker" in data else None)
        if dl_url:
            video_bytes = requests.get(dl_url, timeout=90).content
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print("Berhasil mengunduh via Instance Cobalt!")
            return output_path
    except Exception as e:
        print(f"Cobalt Instance gagal: {e}")

    # 2. Alternative: Gunakan Invidious / Piped API untuk YouTube Shorts
    if "youtube.com" in url or "youtu.be" in url:
        try:
            # Ekstrak Video ID
            video_id = url.split("shorts/")[-1].split("?")[0].split("/")[0]
            piped_api = f"https://pipedapi.kavin.rocks/streams/{video_id}"
            res = requests.get(piped_api, timeout=20).json()
            
            # Cari stream MP4
            video_stream = next((item["url"] for item in res.get("videoStreams", []) if item.get("container") == "m4a" or "mp4" in item.get("mimeType", "")), None)
            if video_stream:
                video_bytes = requests.get(video_stream, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh via Piped API!")
                return output_path
        except Exception as e:
            print(f"Piped API gagal: {e}")

    # 3. Fallback: Gunakan yt-dlp dengan Player Client khusus
    print("Mencoba fallback via yt-dlp dengan Android client...")
    command = [
        "yt-dlp",
        "-o", output_path,
        "-f", "b[ext=mp4]/b",
        "--extractor-args", "youtube:player_client=android",
        "--no-playlist",
        url
    ]
    subprocess.run(command, check=True)
    print("Berhasil mengunduh via yt-dlp Android client!")
    return output_path
def upload_to_facebook_page(page_id, page_token, video_path):
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        'description': DEFAULT_CAPTION,
        'access_token': page_token
    }
    with open(video_path, 'rb') as video_file:
        files = {'source': video_file}
        print(f"Mengunggah ke Halaman ID: {page_id}...")
        response = requests.post(url, data=payload, files=files)
        return response.json()

def main():
    if not os.path.exists(LINKS_FILE):
        print("File links.txt tidak ditemukan.")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    target_index = -1
    target_url = ""
    for idx, line in enumerate(lines):
        if not line.startswith("#DONE"):
            target_index = idx
            target_url = line
            break

    if target_index == -1 or not target_url:
        print("Semua video di links.txt sudah selesai diposting!")
        return

    if not FB_PAGES_DATA:
        print("Error: Secret FB_PAGES_DATA tidak ditemukan.")
        return

    pages = json.loads(FB_PAGES_DATA)
    video_file = "temp_video.mp4"

    try:
        # 1. Download video via Cobalt API
        download_video_via_cobalt(target_url, video_file)

        # 2. Upload ke 10 Facebook Pages
        for page in pages:
            res = upload_to_facebook_page(page['id'], page['token'], video_file)
            print(f"Hasil {page['name']}: {res}")

        # 3. Tandai status #DONE
        lines[target_index] = f"#DONE {target_url}"
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

        print("Berhasil mengunggah video ke semua halaman!")

    except Exception as e:
        print(f"Gagal memproses video: {e}")

    finally:
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    main()
