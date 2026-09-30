import json
import os
import time
import requests


def download_video(url, output_path="temp_video.mp4"):
    """Mengunduh file video dari URL publik atau TikTok/Reels link."""
    print(f"Mengunduh video dari: {url}")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print("Berhasil mengunduh video.")
        return output_path
    except Exception as e:
        print(f"Gagal mengunduh video: {e}")
        return None


def upload_reels_to_facebook(
    page_id, page_token, video_path, caption="Automated Reels Video"
):
    """Mengunggah video ke Facebook Reels dan menunggu proses encoding selesai."""
    print(f"\nMengunggah REELS ke Halaman ID: {page_id}")

    # 1. Inisialisasi Sesi Upload
    init_url = f"https://graph.facebook.com/v20.0/{page_id}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": page_token,
    }

    try:
        init_res = requests.post(init_url, data=init_payload).json()
        if "video_id" not in init_res or "upload_url" not in init_res:
            print(f"Gagal Inisialisasi: {init_res}")
            return None

        video_id = init_res["video_id"]
        upload_url = init_res["upload_url"]

        # 2. Upload File Video (Binary)
        file_size = os.path.getsize(video_path)
        headers = {
            "Authorization": f"OAuth {page_token}",
            "offset": "0",
            "file_size": str(file_size),
        }

        with open(video_path, "rb") as video_file:
            upload_res = requests.post(
                upload_url, headers=headers, data=video_file
            ).json()

        # 3. Publish Reels
        publish_url = f"https://graph.facebook.com/v20.0/{page_id}/video_reels"
        publish_payload = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": page_token,
        }

        finish_res = requests.post(publish_url, data=publish_payload).json()
        print(f"Hasil Upload REELS ke Halaman ID {page_id}: {finish_res}")

        # 4. Pengecekan Status Pemrosesan Video di Server Facebook
        print("Menunggu proses pemrosesan video di server Facebook...")
        status_url = f"https://graph.facebook.com/v20.0/{video_id}?fields=status&access_token={page_token}"

        max_retries = 12  # Cek hingga 2 menit (12 x 10 detik)
        for i in range(max_retries):
            time.sleep(10)
            status_res = requests.get(status_url).json()
            video_status = (
                status_res.get("status", {}).get("video_status", "").lower()
            )

            print(
                f"[{i+1}/{max_retries}] Status Pemrosesan Video ({video_id}): {video_status}"
            )

            if video_status in ["ready", "published"]:
                print(f"Video SELESAI diproses dan terbit: {video_id}")
                return video_id
            elif video_status == "error":
                print(f"Facebook gagal memproses video: {status_res}")
                return None

        print(
            f"Video masih dalam antrean pemrosesan Facebook (ID: {video_id})."
        )
        return video_id

    except Exception as e:
        print(f"Terjadi kesalahan saat unggah: {e}")
        return None


def main():
    input_file = "input_link.txt"

    # Cek keberadaan dan isi input_link.txt
    if not os.path.exists(input_file):
        print(f"File {input_file} tidak ditemukan!")
        return

    with open(input_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print(f"URL Video tidak ditemukan di {input_file}")
        return

    # Mengambil Secret/Environment FB_PAGES_DATA
    fb_pages_json = os.environ.get("FB_PAGES_DATA")
    if not fb_pages_json:
        print("Environment variable FB_PAGES_DATA tidak ditemukan!")
        return

    try:
        pages = json.loads(fb_pages_json)
    except Exception as e:
        print(f"Gagal memuat JSON dari FB_PAGES_DATA: {e}")
        return

    # Proses Setiap URL
    for target_url in urls:
        temp_video_path = "temp_video.mp4"
        downloaded = download_video(target_url, temp_video_path)

        if downloaded and os.path.exists(temp_video_path):
            # Unggah ke semua halaman Facebook yang terkonfigurasi
            for page in pages:
                page_id = page.get("page_id")
                page_token = page.get("access_token")
                caption = page.get("caption", "Automated Reels")

                if page_id and page_token:
                    upload_reels_to_facebook(
                        page_id, page_token, temp_video_path, caption
                    )

            # Hapus file sementara setelah selesai diproses
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)


if __name__ == "__main__":
    main()
