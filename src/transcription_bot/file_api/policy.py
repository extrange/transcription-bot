class Policy:
    """Minio bucket policies."""

    DEFAULT_BUCKET_PLACEHOLDER = "bucket"

    @classmethod
    def public_read_only(
        cls,
        bucket_placeholder: str = DEFAULT_BUCKET_PLACEHOLDER,
    ) -> dict:
        """Return a publicly accessible read-only policy for the bucket."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": f"arn:aws:s3:::{{{bucket_placeholder}}}",
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{{{bucket_placeholder}}}/*",
                },
            ],
        }

    @classmethod
    def none(cls) -> None:
        """Return no policy: the bucket keeps only credentialed access.

        With no bucket policy, objects are reachable only by callers holding the
        MinIO credentials or by a presigned URL. Use this when download links are
        presigned rather than public.
        """

    @classmethod
    def public_read_and_write(
        cls,
        bucket_placeholder: str = DEFAULT_BUCKET_PLACEHOLDER,
    ) -> dict:
        """Return a publicly accessible read and write policy for the bucket."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                    ],
                    "Resource": f"arn:aws:s3:::{{{bucket_placeholder}}}",
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                    ],
                    "Resource": f"arn:aws:s3:::{{{bucket_placeholder}}}/images/*",
                },
            ],
        }
