"""
Data migration utilities for vector databases.
This module provides tools to migrate data between different vector database providers.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document

from .base import VectorDatabaseInterface
from .config import VectorDBConfig, get_vector_db_config
from .factory import VectorDatabaseFactory


class VectorDBMigrator:
    """Utility class for migrating data between vector databases."""

    def __init__(
        self, embedding_model: Embeddings, config: Optional[VectorDBConfig] = None
    ):
        """
        Initialize the migrator.

        Args:
            embedding_model: The embedding model to use
            config: Configuration object (optional, will load from env if not provided)
        """
        self.embedding_model = embedding_model
        self.config = config or get_vector_db_config()

    def migrate_chroma_to_qdrant(
        self,
        chroma_persist_dir: Optional[str] = None,
        backup_chroma: bool = True,
        clear_target: bool = True,
    ) -> bool:
        """
        Migrate data from Chroma to Qdrant.

        Args:
            chroma_persist_dir: Path to Chroma persistence directory (optional)
            backup_chroma: Whether to backup Chroma data before migration
            clear_target: Whether to clear existing Qdrant data

        Returns:
            True if migration was successful, False otherwise
        """
        try:
            print("Starting Chroma to Qdrant migration...")

            # Use provided path or config default
            chroma_dir = chroma_persist_dir or self.config.chroma.persist_directory

            # Check if Chroma data exists
            if not os.path.exists(chroma_dir):
                print(f"No Chroma data found at {chroma_dir}")
                return False

            # Backup Chroma data if requested
            if backup_chroma:
                backup_path = f"{chroma_dir}_backup_{self._get_timestamp()}"
                shutil.copytree(chroma_dir, backup_path)
                print(f"Backed up Chroma data to: {backup_path}")

            # Create Chroma instance to read data
            print("Reading data from Chroma...")
            chroma_db = VectorDatabaseFactory.create(
                self.embedding_model, provider="chroma"
            )
            chroma_db.initialize(clear_existing=False)

            # Get all documents from Chroma
            documents = self._extract_all_documents(chroma_db)

            if not documents:
                print("No documents found in Chroma database")
                return False

            print(f"Found {len(documents)} documents in Chroma")

            # Create Qdrant instance
            print("Setting up Qdrant...")
            qdrant_db = VectorDatabaseFactory.create(
                self.embedding_model, provider="qdrant"
            )
            qdrant_db.initialize(clear_existing=clear_target)

            # Migrate documents to Qdrant
            print("Migrating documents to Qdrant...")
            qdrant_db.add_documents(documents)
            qdrant_db.persist()

            # Verify migration
            qdrant_info = qdrant_db.get_collection_info()
            if qdrant_info.get("vector_count", 0) > 0:
                print(
                    f"Migration successful! {qdrant_info['vector_count']} vectors in Qdrant"
                )
                return True
            else:
                print("Migration may have failed - no vectors found in Qdrant")
                return False

        except Exception as e:
            print(f"Error during migration: {e}")
            return False

    def migrate_qdrant_to_chroma(
        self, backup_qdrant: bool = True, clear_target: bool = True
    ) -> bool:
        """
        Migrate data from Qdrant to Chroma.

        Args:
            backup_qdrant: Whether to backup Qdrant data before migration
            clear_target: Whether to clear existing Chroma data

        Returns:
            True if migration was successful, False otherwise
        """
        try:
            print("Starting Qdrant to Chroma migration...")

            # Backup Qdrant data if requested
            if backup_qdrant and self.config.qdrant.mode == "local":
                backup_path = (
                    f"{self.config.qdrant.path}_backup_{self._get_timestamp()}"
                )
                if os.path.exists(self.config.qdrant.path):
                    shutil.copytree(self.config.qdrant.path, backup_path)
                    print(f"Backed up Qdrant data to: {backup_path}")

            # Create Qdrant instance to read data
            print("Reading data from Qdrant...")
            qdrant_db = VectorDatabaseFactory.create(
                self.embedding_model, provider="qdrant"
            )
            qdrant_db.initialize(clear_existing=False)

            # Get all documents from Qdrant
            documents = self._extract_all_documents(qdrant_db)

            if not documents:
                print("No documents found in Qdrant database")
                return False

            print(f"Found {len(documents)} documents in Qdrant")

            # Create Chroma instance
            print("Setting up Chroma...")
            chroma_db = VectorDatabaseFactory.create(
                self.embedding_model, provider="chroma"
            )
            chroma_db.initialize(clear_existing=clear_target)

            # Migrate documents to Chroma
            print("Migrating documents to Chroma...")
            chroma_db.add_documents(documents)
            chroma_db.persist()

            # Verify migration
            chroma_info = chroma_db.get_collection_info()
            if chroma_info.get("count", 0) > 0:
                print(f"Migration successful! {chroma_info['count']} vectors in Chroma")
                return True
            else:
                print("Migration may have failed - no vectors found in Chroma")
                return False

        except Exception as e:
            print(f"Error during migration: {e}")
            return False

    def _extract_all_documents(self, db: VectorDatabaseInterface) -> List[Document]:
        """
        Extract all documents from a vector database.

        Args:
            db: Vector database instance

        Returns:
            List of all documents in the database
        """
        # This is a simplified approach - in a real scenario, you might need
        # to use database-specific methods to extract all documents
        try:
            # Try to get collection info to estimate document count
            info = db.get_collection_info()
            print(f"Collection info: {info}")

            # For now, return empty list - actual implementation would depend
            # on the specific vector database's ability to list all documents
            # This is a limitation of most vector databases
            print("Warning: Full document extraction not implemented yet")
            print("Consider using backup/restore from raw document sources instead")
            return []

        except Exception as e:
            print(f"Error extracting documents: {e}")
            return []

    def _get_timestamp(self) -> str:
        """Get timestamp string for backup naming."""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def create_backup(self, provider: str, backup_path: Optional[str] = None) -> bool:
        """
        Create a backup of vector database data.

        Args:
            provider: Provider to backup ("qdrant" or "chroma")
            backup_path: Custom backup path (optional)

        Returns:
            True if backup was successful, False otherwise
        """
        try:
            timestamp = self._get_timestamp()

            if provider == "chroma":
                source_path = self.config.chroma.persist_directory
                default_backup = f"{source_path}_backup_{timestamp}"
                target_path = backup_path or default_backup

                if os.path.exists(source_path):
                    shutil.copytree(source_path, target_path)
                    print(f"Chroma backup created: {target_path}")
                    return True
                else:
                    print(f"No Chroma data found at {source_path}")
                    return False

            elif provider == "qdrant":
                if self.config.qdrant.mode == "local":
                    source_path = self.config.qdrant.path
                    default_backup = f"{source_path}_backup_{timestamp}"
                    target_path = backup_path or default_backup

                    if os.path.exists(source_path):
                        shutil.copytree(source_path, target_path)
                        print(f"Qdrant backup created: {target_path}")
                        return True
                    else:
                        print(f"No Qdrant data found at {source_path}")
                        return False
                else:
                    print("Backup not supported for Qdrant server mode")
                    return False
            else:
                print(f"Unknown provider: {provider}")
                return False

        except Exception as e:
            print(f"Error creating backup: {e}")
            return False


def migrate_to_qdrant(embedding_model: Embeddings, backup: bool = True) -> bool:
    """
    Convenience function to migrate from Chroma to Qdrant.

    Args:
        embedding_model: The embedding model to use
        backup: Whether to backup existing data

    Returns:
        True if migration was successful, False otherwise
    """
    migrator = VectorDBMigrator(embedding_model)
    return migrator.migrate_chroma_to_qdrant(backup_chroma=backup)


def migrate_to_chroma(embedding_model: Embeddings, backup: bool = True) -> bool:
    """
    Convenience function to migrate from Qdrant to Chroma.

    Args:
        embedding_model: The embedding model to use
        backup: Whether to backup existing data

    Returns:
        True if migration was successful, False otherwise
    """
    migrator = VectorDBMigrator(embedding_model)
    return migrator.migrate_qdrant_to_chroma(backup_qdrant=backup)
