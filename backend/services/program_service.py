"""
Program service for CRUD operations and business logic.
Handles async database interactions with ownership validation.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.program import Program
from backend.models.user import User


class ProgramService:
    """Service for program management operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize ProgramService with database session.

        Args:
            db: AsyncSession for database operations
        """
        self.db = db

    async def create_program(
        self,
        user_id: UUID,
        name: str,
        platform: str,
        scope: str,
        description: Optional[str] = None,
    ) -> Program:
        """
        Create a new program owned by the current user.

        Args:
            user_id: ID of the program owner
            name: Program name
            platform: Bug bounty platform
            scope: Program scope/targets
            description: Optional program description

        Returns:
            Program: Created program instance

        Raises:
            ValueError: If validation fails
        """
        program = Program(
            name=name,
            platform=platform,
            scope=scope,
            description=description,
            created_by=user_id,
        )
        self.db.add(program)
        await self.db.commit()
        await self.db.refresh(program)
        return program

    async def get_user_programs(
        self,
        user_id: UUID,
    ) -> list[Program]:
        """
        Get all programs owned by a specific user.

        Args:
            user_id: ID of the user

        Returns:
            list[Program]: List of programs owned by the user
        """
        result = await self.db.execute(
            select(Program).where(Program.created_by == user_id).order_by(Program.created_at.desc())
        )
        return result.scalars().all()

    async def get_program_by_id(
        self,
        program_id: UUID,
        user_id: UUID,
    ) -> Optional[Program]:
        """
        Get a specific program if owned by the user.

        Args:
            program_id: ID of the program
            user_id: ID of the requesting user

        Returns:
            Program: Program instance if found and owned by user, None otherwise
        """
        result = await self.db.execute(
            select(Program).where(
                and_(
                    Program.id == program_id,
                    Program.created_by == user_id,
                )
            )
        )
        return result.scalars().first()

    async def update_program(
        self,
        program_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        platform: Optional[str] = None,
        scope: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Program]:
        """
        Update a program if owned by the user.

        Args:
            program_id: ID of the program
            user_id: ID of the requesting user
            name: Updated program name
            platform: Updated platform
            scope: Updated scope
            description: Updated description

        Returns:
            Program: Updated program instance if found and owned by user, None otherwise
        """
        program = await self.get_program_by_id(program_id, user_id)
        if not program:
            return None

        if name is not None:
            program.name = name
        if platform is not None:
            program.platform = platform
        if scope is not None:
            program.scope = scope
        if description is not None:
            program.description = description

        await self.db.commit()
        await self.db.refresh(program)
        return program

    async def delete_program(
        self,
        program_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a program if owned by the user.

        Args:
            program_id: ID of the program
            user_id: ID of the requesting user

        Returns:
            bool: True if deleted, False if not found or not owned by user
        """
        program = await self.get_program_by_id(program_id, user_id)
        if not program:
            return False

        await self.db.delete(program)
        await self.db.commit()
        return True

    async def count_user_programs(
        self,
        user_id: UUID,
    ) -> int:
        """
        Get count of programs owned by a user.

        Args:
            user_id: ID of the user

        Returns:
            int: Number of programs owned by user
        """
        result = await self.db.execute(
            select(Program).where(Program.created_by == user_id)
        )
        return len(result.scalars().all())
