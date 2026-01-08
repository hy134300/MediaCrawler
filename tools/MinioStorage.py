from minio import Minio


class MinioStorage:
    def __init__(self):
        self.client = Minio(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        self.bucket = "ai-companion"
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, file_path: str, object_name: str) -> str:
        self.client.fput_object(
            bucket_name=self.bucket,
            object_name=object_name,
            file_path=file_path,
            content_type="application/octet-stream"
        )
        return f"http://localhost:9000/{self.bucket}/{object_name}"
