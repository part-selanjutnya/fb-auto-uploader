import os
import json
import requests
import subprocess

def download_video_with_curl(url, output_path='temp_video.mp4'):
    print(f"Mengunduh file MP4 via curl dari: {url}...")
    cmd = [
        'curl', '-sL',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        url,
        '-o', output_path
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Gagal mengunduh file video dari Catbox menggunakan curl.")
    print("Unduhan berhasil.")
    return output_path

def upload_video_to_page(page_id, page_token, file_path, title, description):
    # Wajib menggunakan subdomain 'graph-video.facebook.com' untuk pengunggahan video
    url = f"https://graph-video.facebook.com/v26.0/{page_id}/videos"
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
                # 1. Unduh file lokal via curl
                download_video_with_curl(video_url, temp_file)

                # 2. Unggah file ke seluruh halaman Facebook via graph-video.facebook.com
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
