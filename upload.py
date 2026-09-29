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
        'overwrites': True
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
        print("Error: FB_PAGES_DATA tidak ditemukan di secrets!")
        return

    pages = json.loads(pages_json)

    if not os.path.exists('videos.json'):
        print("Error: videos.json tidak ditemukan!")
        return

    with open('videos.json', 'r', encoding='utf-8') as f:
        videos = json.load(f)

    updated = False
    for video in videos:
        if video.get('status') == 'pending':
            video_url = video.get('url')
            title = video.get('title', '')
            description = video.get('description', '')

            print(f"Memproses video: {title}")
            
            temp_file = 'temp_video.mp4'
            try:
                # Unduh otomatis dari YouTube
                download_youtube_video(video_url, temp_file)

                # Unggah ke seluruh halaman Facebook
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
                        print(f"-> Sukses! Video ID: {res['id']}")
                    else:
                        print(f"-> Gagal: {res}")

                # Hapus file sementara setelah selesai
                if os.path.exists(temp_file):
                    os.remove(temp_file)

                video['status'] = 'completed'
                updated = True
                break  # Memproses 1 video per siklus jadwal

            except Exception as e:
                print(f"Error saat memproses video: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    if updated:
        with open('videos.json', 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        print("videos.json berhasil diperbarui.")

if __name__ == '__main__':
    main()
