import os
import time
import tempfile
import logging

logger = logging.getLogger(__name__)

def find_uploaded_file(filename, return_search_paths=False):
    """
    Try to find a recently uploaded file in CKAN's storage directories.
    
    Args:
        filename: The name of the file to find
        return_search_paths: If True, return the list of paths that were searched instead of the file path
        
    Returns:
        If return_search_paths is False (default): Full path to the file if found, None otherwise
        If return_search_paths is True: List of paths that were searched
    """
    try:
        # Common upload paths in CKAN
        upload_paths = []
        storage_path = None
        
        # Try to get the storage path from CKAN config
        try:
            try:
                from ckan.common import config
                storage_path = config.get('ckan.storage_path')
                if storage_path:
                    logger.info(f"Found CKAN storage path from config: {storage_path}")
            except Exception:
                pass
                
            # Try alternative methods to get storage path
            if not storage_path:
                try:
                    import ckan.lib.uploader as uploader
                    storage_path = uploader.get_storage_path()
                    if storage_path:
                        logger.info(f"Found CKAN storage path from uploader: {storage_path}")
                except Exception:
                    pass
        except Exception as e:
            logger.info(f"Error getting CKAN storage path: {str(e)}")
            
        if storage_path:
            # Add standard paths
            upload_paths.extend([
                os.path.join(storage_path, 'storage', 'uploads'),
                os.path.join(storage_path, 'uploads'),
                storage_path
            ])
            
            # Add cloud storage specific paths
            cloud_paths = [
                os.path.join(storage_path, 'storage', 'cloudstorage'),
                os.path.join(storage_path, 'cloudstorage'),
                os.path.join(storage_path, 'storage', 'cloudstorage', 'container')
            ]
            
            for cloud_path in cloud_paths:
                if os.path.exists(cloud_path):
                    upload_paths.append(cloud_path)
                    logger.info(f"Found cloud storage path: {cloud_path}")
                    
                    # Check for container subdirectory which is often where files are actually stored
                    container_path = os.path.join(cloud_path, 'container')
                    if os.path.exists(container_path):
                        upload_paths.append(container_path)
                        logger.info(f"Found cloud storage container path: {container_path}")
        
        # Fallback paths
        upload_paths.extend([
            '/var/lib/ckan/default/storage/uploads',
            '/var/lib/ckan/default/storage/cloudstorage',  # Common cloud storage path
            '/usr/lib/ckan/default/storage/uploads',
            '/usr/lib/ckan/default/storage/cloudstorage',
            '/tmp/uploads',
            tempfile.gettempdir()
        ])
        
        logger.info(f"Searching for file {filename} in paths: {upload_paths}")
        
        # Search in each path
        for base_path in upload_paths:
            if not os.path.exists(base_path):
                continue
                
            # Direct file in base path
            file_path = os.path.join(base_path, filename)
            if os.path.exists(file_path):
                logger.info(f"Found file at: {file_path}")
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    logger.info(f"File size: {file_size} bytes")
                    return file_path
                else:
                    logger.info(f"Found file at {file_path} but size is 0 bytes - continuing search")
            
            # Check if this is a cloudstorage path based on name
            is_cloudstorage_path = ('cloudstorage' in base_path.lower())
            if is_cloudstorage_path:
                logger.info(f"Searching CloudStorage path: {base_path}")
            
            # Special case for CloudStorage - check container structure
            cloud_container_path = os.path.join(base_path, 'container')
            if os.path.exists(cloud_container_path):
                logger.info(f"Found cloud storage container path: {cloud_container_path}")
                try:
                    # CloudStorage often organizes files in random subdirectories
                    # List directories to see what's available
                    container_contents = os.listdir(cloud_container_path)
                    logger.info(f"Container contents: {container_contents}")
                    
                    # Walk the directory tree looking for matches
                    for root, dirs, files in os.walk(cloud_container_path):
                        logger.debug(f"Checking directory: {root}")
                        
                        # Check for any file that might match our filename
                        for file in files:
                            # Log all non-empty files to help diagnosis
                            full_path = os.path.join(root, file)
                            file_size = os.path.getsize(full_path)
                            if file_size > 0:
                                logger.debug(f"Found file: {file}, size: {file_size} bytes")
                            
                            # CloudStorage sometimes adds random prefixes/suffixes, so check if our filename is contained
                            # In the filename or if the cloudstorage ID is in our filename
                            filename_match = filename in file
                            reverse_match = file in filename
                            name_similarity = filename_similarity(filename, file)
                            
                            if filename_match or reverse_match or name_similarity > 0.6:
                                logger.info(f"Found potential match: {full_path}, size: {file_size} bytes")
                                logger.info(f"Match type: direct={filename_match}, reverse={reverse_match}, similarity={name_similarity}")
                                
                                if file_size > 0:
                                    logger.info(f"Found cloud storage file match at: {full_path}")
                                    return full_path
                except Exception as e:
                    logger.info(f"Error checking cloud storage container: {str(e)}")
            
            # Search in subdirectories (recent uploads)
            try:
                # First do a quick check of the immediate directory to avoid deep walks if possible
                try:
                    dir_contents = os.listdir(base_path)
                    if len(dir_contents) > 0:
                        logger.debug(f"Directory contents ({len(dir_contents)} files/dirs): {dir_contents[:10]}...")
                except Exception:
                    pass
                
                for root, dirs, files in os.walk(base_path):
                    # Check for exact match first
                    if filename in files:
                        full_path = os.path.join(root, filename)
                        file_time = os.path.getmtime(full_path)
                        file_size = os.path.getsize(full_path)
                        time_diff = time.time() - file_time
                        logger.info(f"Found exact match: {full_path}, size: {file_size} bytes, age: {time_diff:.1f} seconds")
                        
                        # Check if file is recent (within last 30 minutes) and not empty
                        if time_diff < 1800 and file_size > 0:
                            logger.info(f"Found recent file at: {full_path}, size: {file_size} bytes")
                            return full_path
                    
                    # Then check for partial matches (especially for CloudStorage which might add identifiers)
                    if is_cloudstorage_path or 'tmp' in base_path.lower():
                        for file in files:
                            # Check if the file contains the uploaded filename (for CloudStorage)
                            name_similarity = filename_similarity(filename, file)
                            if filename in file or file in filename or name_similarity > 0.6:
                                full_path = os.path.join(root, file)
                                file_time = os.path.getmtime(full_path)
                                file_size = os.path.getsize(full_path)
                                time_diff = time.time() - file_time
                                
                                # Make sure it's recent and not empty
                                if time_diff < 1800 and file_size > 0:
                                    logger.info(f"Found partial match: {full_path}, size: {file_size} bytes, age: {time_diff:.1f} seconds")
                                    logger.info(f"Similarity score: {name_similarity}")
                                    return full_path
            except Exception as e:
                logger.info(f"Error walking directory {base_path}: {str(e)}")
                continue
        
        logger.info(f"File {filename} not found in any upload paths")
        # Return the search paths if requested, otherwise return None
        if return_search_paths:
            return upload_paths
        return None
        
    except Exception as e:
        logger.error(f"Error searching for uploaded file {filename}: {str(e)}")
        if return_search_paths:
            return []
        return None


def filename_similarity(name1, name2):
    """Calculate a simple similarity score between two filenames."""
    # Extract base filename without path or extension
    base1 = os.path.splitext(os.path.basename(name1))[0].lower()
    base2 = os.path.splitext(os.path.basename(name2))[0].lower()
    
    # Count shared characters
    shared_chars = sum(c in base2 for c in base1)
    
    # Calculate similarity as ratio of shared characters to average length
    avg_len = (len(base1) + len(base2)) / 2
    if avg_len == 0:
        return 0
        
    return shared_chars / avg_len
