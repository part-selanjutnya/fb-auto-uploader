import os
import json
import requests
import yt_dlp

def download_youtube_video(youtube_url, output_path='temp_video.mp4'):
    print(f"Mengunduh video dari YouTube: {youtube_url}...")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': False,
        'overwrites': True,
        'nocheckcertificate': True,
        # Bypass deteksi bot YouTube dengan menyamar sebagai client Android/iOS/mweb
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return output_path

def upload_video_to_page(page_id, page_token, file_path, title, description):
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        'title': title,
        'description': description,
        'access_token': page_token
    }
    with open(file_path, 'rb') as f:
        files = {'source': f}
        response = requests.post(url, data=payload, files=files)
    return response.json()

def main():
    pages_json = os.environ.get('FB_PAGES_DATA')
    if not pages_json:
        raise ValueError("Error: Secret 'FB_PAGES_DATA' tidak ditemukan atau kosong!")

    pages = json.loads(pages_json)

    if not os.path.exists('videos.json'):
        raise FileNotFoundError("Error: File 'videos.json' tidak ditemukan!")

    with open('videos.json', 'r', encoding='utf-8') as f:
        videos = json.load(f)

    updated = False
    for video in videos:
        if video.get('status') == 'pending':
            video_url = video.get('url')
            title = video.get('title', '')
            description = video.get('description', '')

            print("==========================================")
            print(f"Memproses video: {title}")
            print(f"URL: {video_url}")
            print("==========================================")
            
            temp_file = 'temp_video.mp4'
            try:
                # 1. Jika URL berupa link langsung file MP4
                if video_url.endswith('.mp4') or ('http' in video_url and not ('youtube.com' in video_url or 'youtu.be' in video_url)):
                    print("Mengunduh langsung dari URL MP4...")
                    r = requests.get(video_url, stream=True)
                    with open(temp_file, 'wb') as f_out:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f_out.write(chunk)
                else:
                    # 2. Unduh dari YouTube Shorts
                    download_youtube_video(video_url, temp_file)

                # Unggah ke seluruh halaman Facebook
                success_count = 0
                for page in pages:
                    print(f"Mengunggah ke halaman: {page['name']} ({page['id']})...")
                    res = upload_video_to_page(
                        page['id'],
                        page['token'],
                        temp_file,
                        title,
                        description
                    )
                    
                    if 'id' in res:
                        print(f" -> Sukses! Video ID: {res['id']}")
                        success_count += 1
                    else:
                        print(f" -> Gagal unggah ke {page['name']}: {json.dumps(res)}")

                if os.path.exists(temp_file):
                    os.remove(temp_file)

                if success_count > 0:
                    video['status'] = 'completed'
                    updated = True
                    break
                else:
                    raise RuntimeError("Gagal mengunggah ke halaman Facebook. Periksa token/izin halaman Anda.")

            except Exception as e:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise RuntimeError(f"Gagal memproses video: {e}")

    if updated:
        with open('videos.json', 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        print("videos.json berhasil diperbarui menjadi completed.")

if __name__ == '__main__':
    main()
