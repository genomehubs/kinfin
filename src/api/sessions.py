import hashlib
import json
import logging
import os
import shutil
import signal
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger("kinfin_logger")


class QueryManager:
    """
    A class to manage query sessions, including creation, retrieval, and cleanup of session directories.
    """

    def __init__(self, expiration_hours: int = 24) -> None:
        """Initializes the QueryManager with the specified expiration time for sessions."""
        self.results_base_dir = ""
        self.cluster_f = ""
        self.sequence_ids_f = ""
        self.taxon_idx_mapping_file = ""
        self.nodesdb_f = ""
        self.pfam_mapping_f = ""
        self.ipr_mapping_f = ""
        self.go_mapping_f = ""

        self.expiration_hours = expiration_hours
        os.makedirs(self.results_base_dir, exist_ok=True)

        self.cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def get_session_id(self, query: List[Dict[str, str]]) -> str:
        """
        Generate a unique session ID based on the query.

        Args:
            query (List[Dict[str, str]]): The query for which to generate a session ID.

        Returns:
            str: The generated session ID.
        """
        query_json = json.dumps(query, sort_keys=True)
        return hashlib.md5(query_json.encode()).hexdigest()

    def get_or_create_session(self, query: List[Dict[str, str]]) -> Tuple[str, str]:
        """
        Get or create a session directory based on the query.

        Args:
            query (List[Dict[str, str]]): The query for which to get or create a session.

        Returns:
            tuple: The session ID and the session directory path.
        """
        session_id = self.get_session_id(query)
        session_dir = os.path.join(self.results_base_dir, session_id)

        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        else:
            os.utime(session_dir, None)

        return session_id, session_dir

    def get_session_dir(self, session_id: str) -> Optional[str]:
        """
        Get the directory path of an existing session.

        Args:
            session_id (str): The session ID for which to get the directory path.

        Returns:
            str: The session directory path, or None if the session does not exist.
        """
        session_dir = os.path.join(self.results_base_dir, session_id)
        if os.path.exists(session_dir):
            os.utime(session_dir, None)
            return session_dir
        return None

    def cleanup_loop(self) -> None:
        """The main loop for periodically cleaning up expired sessions."""
        while True:
            self.cleanup_expired_sessions()
            time.sleep(3600)

    def cleanup_expired_sessions(self) -> None:
        """Clean up sessions that have expired based on the expiration time."""
        now = datetime.now()
        for session_id in os.listdir(self.results_base_dir):
            session_dir = os.path.join(self.results_base_dir, session_id)
            mod_time = datetime.fromtimestamp(os.path.getmtime(session_dir))

            if now - mod_time > timedelta(hours=self.expiration_hours):
                shutil.rmtree(session_dir)

    def __exit__(self, _, __) -> None:
        """Cleanup all sessions when exiting due to signal"""
        shutil.rmtree(self.results_base_dir)
        exit(0)


query_manager = QueryManager()

signal.signal(signal.SIGINT, query_manager.__exit__)
signal.signal(signal.SIGTERM, query_manager.__exit__)
