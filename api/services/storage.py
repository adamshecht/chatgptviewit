#!/usr/bin/env python3
"""
Cloud Storage Manager for S3/GCS integration
Handles document storage and pre-signed URL generation
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
logger = logging.getLogger(__name__)

class StorageManager:
    """Manages cloud storage operations for documents."""
    
    def __init__(self, storage_type: str = "s3"):
        """Initialize storage manager.
        
        Args:
            storage_type: "s3" or "gcs" for storage provider
        """
        self.storage_type = storage_type.lower()
        self.bucket_name = os.getenv('STORAGE_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not self.bucket_name:
            raise ValueError("STORAGE_BUCKET_NAME environment variable required")
        
        # Initialize storage client based on type
        if self.storage_type == "s3":
            self._init_s3_client()
        elif self.storage_type == "gcs":
            self._init_gcs_client()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
    
    def _init_s3_client(self):
        """Initialize AWS S3 client."""
        try:
            import boto3
            self.client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            logger.info("S3 client initialized")
        except ImportError:
            raise ImportError("boto3 required for S3 storage")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def _init_gcs_client(self):
        """Initialize Google Cloud Storage client."""
        try:
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info("GCS client initialized")
        except ImportError:
            raise ImportError("google-cloud-storage required for GCS storage")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise
    
    def generate_storage_key(self, company_id: str, municipality: str, meeting_guid: str, 
                           filename: str) -> str:
        """Generate storage key for document.
        
        Args:
            company_id: Company identifier
            municipality: Municipality name
            meeting_guid: Meeting GUID
            filename: Original filename
            
        Returns:
            Storage key for cloud storage
        """
        # Clean and normalize components
        company_id = company_id.lower().replace(' ', '_')
        municipality = municipality.lower().replace(' ', '_')
        meeting_guid = meeting_guid.replace('/', '_')
        
        # Generate storage key: company/municipality/meeting/filename
        storage_key = f"{company_id}/{municipality}/{meeting_guid}/{filename}"
        
        return storage_key
    
    def upload_document(self, file_path: str, storage_key: str, 
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Upload document to cloud storage.
        
        Args:
            file_path: Local file path to upload
            storage_key: Storage key for cloud storage
            metadata: Optional metadata to store with file
            
        Returns:
            Dict with upload results including etag, size, etc.
        """
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return self.upload_document_from_content(file_content, storage_key, metadata)
            
        except Exception as e:
            logger.error(f"Failed to upload document {storage_key}: {e}")
            raise
    
    def upload_document_from_content(self, content: bytes, storage_key: str, 
                                   metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Upload document content to cloud storage.
        
        Args:
            content: File content as bytes
            storage_key: Storage key for cloud storage
            metadata: Optional metadata to store with file
            
        Returns:
            Dict with upload results including etag, size, etc.
        """
        try:
            # Calculate file hash
            content_hash = hashlib.md5(content).hexdigest()
            size_bytes = len(content)
            
            # Upload to cloud storage
            if self.storage_type == "s3":
                result = self._upload_to_s3(content, storage_key, metadata)
            else:  # GCS
                result = self._upload_to_gcs(content, storage_key, metadata)
            
            # Add calculated metadata
            result.update({
                'content_hash': content_hash,
                'size_bytes': size_bytes,
                'storage_key': storage_key,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Uploaded document: {storage_key} ({size_bytes} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload document {storage_key}: {e}")
            raise
    
    def _upload_to_s3(self, content: bytes, storage_key: str, 
                      metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Upload to S3 with encryption."""
        try:
            response = self.client.put_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Body=content,
                Metadata=metadata or {},
                ServerSideEncryption='AES256'  # SSE-S3 encryption
            )
            
            return {
                'etag': response['ETag'].strip('"'),
                'version_id': response.get('VersionId'),
                'storage_type': 's3',
                'encryption': 'AES256'
            }
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def _upload_to_gcs(self, content: bytes, storage_key: str, 
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Upload to Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_key)
            
            # Set metadata if provided
            if metadata:
                blob.metadata = metadata
            
            blob.upload_from_string(content)
            
            return {
                'etag': blob.etag,
                'generation': blob.generation,
                'storage_type': 'gcs'
            }
            
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise
    
    def generate_presigned_url(self, storage_key: str, 
                              expiration_seconds: int = 3600) -> str:
        """Generate pre-signed URL for document access.
        
        Args:
            storage_key: Storage key for document
            expiration_seconds: URL expiration time in seconds
            
        Returns:
            Pre-signed URL for document access
        """
        try:
            if self.storage_type == "s3":
                return self._generate_s3_presigned_url(storage_key, expiration_seconds)
            else:  # GCS
                return self._generate_gcs_presigned_url(storage_key, expiration_seconds)
                
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {storage_key}: {e}")
            raise
    
    def _generate_s3_presigned_url(self, storage_key: str, 
                                   expiration_seconds: int) -> str:
        """Generate S3 pre-signed URL."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': storage_key
                },
                ExpiresIn=expiration_seconds
            )
            return url
        except Exception as e:
            logger.error(f"S3 presigned URL generation failed: {e}")
            raise
    
    def _generate_gcs_presigned_url(self, storage_key: str, 
                                    expiration_seconds: int) -> str:
        """Generate GCS pre-signed URL."""
        try:
            blob = self.bucket.blob(storage_key)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.utcnow() + timedelta(seconds=expiration_seconds),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"GCS presigned URL generation failed: {e}")
            raise
    
    def download_document(self, storage_key: str, local_path: str) -> bool:
        """Download document from cloud storage.
        
        Args:
            storage_key: Storage key for document
            local_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.storage_type == "s3":
                return self._download_from_s3(storage_key, local_path)
            else:  # GCS
                return self._download_from_gcs(storage_key, local_path)
                
        except Exception as e:
            logger.error(f"Failed to download document {storage_key}: {e}")
            return False
    
    def _download_from_s3(self, storage_key: str, local_path: str) -> bool:
        """Download from S3."""
        try:
            self.client.download_file(self.bucket_name, storage_key, local_path)
            logger.info(f"Downloaded from S3: {storage_key} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return False
    
    def _download_from_gcs(self, storage_key: str, local_path: str) -> bool:
        """Download from GCS."""
        try:
            blob = self.bucket.blob(storage_key)
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded from GCS: {storage_key} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return False
    
    def delete_document(self, storage_key: str) -> bool:
        """Delete document from cloud storage.
        
        Args:
            storage_key: Storage key for document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.storage_type == "s3":
                self.client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            else:  # GCS
                blob = self.bucket.blob(storage_key)
                blob.delete()
            
            logger.info(f"Deleted document: {storage_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {storage_key}: {e}")
            return False
    
    def document_exists(self, storage_key: str) -> bool:
        """Check if document exists in cloud storage.
        
        Args:
            storage_key: Storage key for document
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            if self.storage_type == "s3":
                self.client.head_object(Bucket=self.bucket_name, Key=storage_key)
            else:  # GCS
                blob = self.bucket.blob(storage_key)
                return blob.exists()
            
            return True
            
        except Exception:
            return False 