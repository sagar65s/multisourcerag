import asyncio
from pathlib import Path
import shutil
from uuid import uuid4


class PrivateStorageService:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    async def save(self, owner_id: str, extension: str, content: bytes) -> str:
        safe_owner = "".join(char for char in owner_id if char.isalnum() or char in {"-", "_"})
        if not safe_owner:
            raise ValueError("Invalid storage owner")
        directory = (self.root / safe_owner).resolve()
        if self.root not in directory.parents:
            raise ValueError("Unsafe storage path")
        await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True, mode=0o700)
        path = directory / f"{uuid4().hex}{extension}"
        await asyncio.to_thread(path.write_bytes, content)
        await asyncio.to_thread(path.chmod, 0o600)
        return str(path)

    async def delete(self, stored_path: str) -> bool:
        path = Path(stored_path).resolve()
        if self.root != path and self.root not in path.parents:
            return False
        if path.is_file():
            await asyncio.to_thread(path.unlink)
            return True
        return False

    async def delete_owner(self, owner_id: str) -> None:
        safe_owner = "".join(char for char in owner_id if char.isalnum() or char in {"-", "_"})
        if not safe_owner: raise ValueError("Invalid storage owner")
        directory = (self.root / safe_owner).resolve()
        if self.root not in directory.parents: raise ValueError("Unsafe storage path")
        if directory.is_dir(): await asyncio.to_thread(shutil.rmtree, directory)
