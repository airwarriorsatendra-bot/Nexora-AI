"""Regression tests for the asynchronous research prospect repository."""

from __future__ import annotations

import tempfile
import unittest
import asyncio
from pathlib import Path

from src.research.domain.prospect import Prospect
from src.research.repositories.prospect_repository import ProspectRepository


class ProspectRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.repository = ProspectRepository(
            Path(self._temporary_directory.name) / "research.db"
        )

    async def asyncTearDown(self) -> None:
        self._temporary_directory.cleanup()

    async def test_save_find_update_and_delete(self) -> None:
        created = await self.repository.save(
            Prospect(
                domain="example.com",
                url="https://example.com",
                title="Original",
                email="editor@example.com",
            )
        )

        self.assertTrue(await self.repository.exists_by_domain("www.example.com"))
        found = await self.repository.find_by_domain("example.com")
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.prospect_id, created.prospect_id)
        self.assertEqual(str(found.email), "editor@example.com")

        updated = await self.repository.update(
            found.model_copy(update={"title": "Updated"})
        )
        self.assertEqual(updated.prospect_id, created.prospect_id)
        self.assertEqual(updated.title, "Updated")
        self.assertTrue(await self.repository.delete(updated.prospect_id))
        self.assertFalse(await self.repository.exists_by_domain("example.com"))

    async def test_bulk_save_deduplicates_by_domain_without_changing_identity(self) -> None:
        first = Prospect(
            domain="example.com",
            url="https://example.com",
            title="First",
        )
        replacement = Prospect(
            domain="www.example.com",
            url="https://example.com/about",
            title="Replacement",
        )

        self.assertEqual(await self.repository.save_many([first, replacement]), 2)
        all_prospects = await self.repository.find_all()
        self.assertEqual(len(all_prospects), 1)
        self.assertEqual(all_prospects[0].prospect_id, first.prospect_id)
        self.assertEqual(all_prospects[0].title, "Replacement")

    async def test_concurrent_saves_are_transaction_safe(self) -> None:
        prospects = [
            Prospect(
                domain=f"example-{index}.com",
                url=f"https://example-{index}.com",
            )
            for index in range(12)
        ]

        await asyncio.gather(
            *(self.repository.save(prospect) for prospect in prospects)
        )

        self.assertEqual(len(await self.repository.find_all()), len(prospects))


if __name__ == "__main__":
    unittest.main()
