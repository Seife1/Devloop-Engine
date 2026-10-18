"""Project context model for MCP-native LearnLoop.

This module defines the ProjectContext dataclass that represents metadata about
a user's project including path, technologies, readiness level, and learning history.

Requirements:
- 1.1: Project detection and context loading
- 1.6: Load existing project context
- 23.1: Enforce readiness_level between 1 and 4
- 23.2: Enforce explained_commits <= total_commits
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Technology:
    """Represents a detected technology in a project."""
    
    name: str
    version: Optional[str] = None
    category: Optional[str] = None  # e.g., "language", "framework", "tool"
    
    def __post_init__(self):
        """Validate technology fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Technology name cannot be empty")


@dataclass
class ProjectContext:
    """Metadata about a user's project for learning tracking.
    
    This dataclass stores all relevant information about a project including
    its location, detected technologies, readiness level, and learning metrics.
    
    Attributes:
        id: Unique identifier for the project
        name: Human-readable project name
        repo_path: Absolute path to the project repository
        technologies: List of detected technologies in the project
        readiness_level: User competency level (1-4)
        is_new: Whether this is a newly initialized project
        last_accessed: Timestamp of last project access
        git_root: Path to git repository root, if detected
        total_commits: Total number of commits tracked
        explained_commits: Number of commits with recorded explanations
        knowledge_items_count: Number of documented knowledge items
    
    Validation Rules:
        - readiness_level must be between 1 and 4 inclusive (Requirement 23.1)
        - repo_path must be absolute and exist (Requirement 1.1)
        - last_accessed must not be in the future
        - explained_commits must be <= total_commits (Requirement 23.2)
    """
    
    id: UUID
    name: str
    repo_path: Path
    technologies: list[Technology] = field(default_factory=list)
    readiness_level: int = 1
    is_new: bool = False
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    git_root: Optional[Path] = None
    total_commits: int = 0
    explained_commits: int = 0
    knowledge_items_count: int = 0
    
    def __post_init__(self):
        """Validate ProjectContext fields after initialization.
        
        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate readiness_level (Requirement 23.1)
        if not isinstance(self.readiness_level, int):
            raise ValueError(
                f"readiness_level must be an integer, got {type(self.readiness_level).__name__}"
            )
        if not 1 <= self.readiness_level <= 4:
            raise ValueError(
                f"readiness_level must be between 1 and 4, got {self.readiness_level}"
            )
        
        # Validate repo_path exists (Requirement 1.1)
        if not isinstance(self.repo_path, Path):
            self.repo_path = Path(self.repo_path)
        
        if not self.repo_path.is_absolute():
            raise ValueError(
                f"repo_path must be absolute, got relative path: {self.repo_path}"
            )
        
        if not self.repo_path.exists():
            raise ValueError(
                f"repo_path must exist: {self.repo_path}"
            )
        
        if not self.repo_path.is_dir():
            raise ValueError(
                f"repo_path must be a directory: {self.repo_path}"
            )
        
        # Validate git_root if provided
        if self.git_root is not None:
            if not isinstance(self.git_root, Path):
                self.git_root = Path(self.git_root)
            
            if not self.git_root.is_absolute():
                raise ValueError(
                    f"git_root must be absolute, got relative path: {self.git_root}"
                )
        
        # Validate last_accessed is not in future
        if self.last_accessed > datetime.now(timezone.utc):
            raise ValueError(
                f"last_accessed cannot be in the future: {self.last_accessed}"
            )
        
        # Validate explained_commits <= total_commits (Requirement 23.2)
        if self.explained_commits < 0:
            raise ValueError(
                f"explained_commits must be non-negative, got {self.explained_commits}"
            )
        
        if self.total_commits < 0:
            raise ValueError(
                f"total_commits must be non-negative, got {self.total_commits}"
            )
        
        if self.explained_commits > self.total_commits:
            raise ValueError(
                f"explained_commits ({self.explained_commits}) cannot exceed "
                f"total_commits ({self.total_commits})"
            )
        
        # Validate knowledge_items_count
        if self.knowledge_items_count < 0:
            raise ValueError(
                f"knowledge_items_count must be non-negative, got {self.knowledge_items_count}"
            )
        
        # Validate name is not empty
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")
    
    @classmethod
    def create_new(
        cls,
        name: str,
        repo_path: Path,
        git_root: Optional[Path] = None,
        technologies: Optional[list[Technology]] = None,
    ) -> "ProjectContext":
        """Create a new ProjectContext for a newly initialized project.
        
        Args:
            name: Human-readable project name
            repo_path: Absolute path to the project repository
            git_root: Path to git repository root, if detected
            technologies: List of detected technologies
        
        Returns:
            A new ProjectContext instance with is_new=True
        
        Raises:
            ValueError: If validation fails
        """
        return cls(
            id=uuid4(),
            name=name,
            repo_path=repo_path,
            technologies=technologies or [],
            readiness_level=1,
            is_new=True,
            last_accessed=datetime.now(timezone.utc),
            git_root=git_root,
            total_commits=0,
            explained_commits=0,
            knowledge_items_count=0,
        )
    
    def to_dict(self) -> dict:
        """Serialize ProjectContext to a dictionary.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "repo_path": str(self.repo_path),
            "technologies": [
                {
                    "name": tech.name,
                    "version": tech.version,
                    "category": tech.category,
                }
                for tech in self.technologies
            ],
            "readiness_level": self.readiness_level,
            "is_new": self.is_new,
            "last_accessed": self.last_accessed.isoformat(),
            "git_root": str(self.git_root) if self.git_root else None,
            "total_commits": self.total_commits,
            "explained_commits": self.explained_commits,
            "knowledge_items_count": self.knowledge_items_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectContext":
        """Deserialize ProjectContext from a dictionary.
        
        Args:
            data: Dictionary containing serialized ProjectContext data
        
        Returns:
            ProjectContext instance
        
        Raises:
            ValueError: If deserialization or validation fails
            KeyError: If required fields are missing
        """
        # Parse technologies
        technologies = []
        for tech_data in data.get("technologies", []):
            technologies.append(
                Technology(
                    name=tech_data["name"],
                    version=tech_data.get("version"),
                    category=tech_data.get("category"),
                )
            )
        
        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            repo_path=Path(data["repo_path"]),
            technologies=technologies,
            readiness_level=data["readiness_level"],
            is_new=data.get("is_new", False),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            git_root=Path(data["git_root"]) if data.get("git_root") else None,
            total_commits=data.get("total_commits", 0),
            explained_commits=data.get("explained_commits", 0),
            knowledge_items_count=data.get("knowledge_items_count", 0),
        )
    
    def update_metrics(
        self,
        total_commits: Optional[int] = None,
        explained_commits: Optional[int] = None,
        knowledge_items_count: Optional[int] = None,
    ) -> None:
        """Update project metrics with validation.
        
        Args:
            total_commits: New total commit count (if provided)
            explained_commits: New explained commit count (if provided)
            knowledge_items_count: New knowledge items count (if provided)
        
        Raises:
            ValueError: If updated values violate constraints
        """
        # Temporarily store old values in case we need to rollback
        old_total = self.total_commits
        old_explained = self.explained_commits
        old_items = self.knowledge_items_count
        
        try:
            if total_commits is not None:
                if total_commits < 0:
                    raise ValueError(f"total_commits must be non-negative, got {total_commits}")
                self.total_commits = total_commits
            
            if explained_commits is not None:
                if explained_commits < 0:
                    raise ValueError(f"explained_commits must be non-negative, got {explained_commits}")
                self.explained_commits = explained_commits
            
            if knowledge_items_count is not None:
                if knowledge_items_count < 0:
                    raise ValueError(f"knowledge_items_count must be non-negative, got {knowledge_items_count}")
                self.knowledge_items_count = knowledge_items_count
            
            # Validate constraint: explained_commits <= total_commits
            if self.explained_commits > self.total_commits:
                raise ValueError(
                    f"explained_commits ({self.explained_commits}) cannot exceed "
                    f"total_commits ({self.total_commits})"
                )
        
        except ValueError:
            # Rollback on validation failure
            self.total_commits = old_total
            self.explained_commits = old_explained
            self.knowledge_items_count = old_items
            raise
    
    def update_readiness_level(self, new_level: int) -> None:
        """Update readiness level with validation.
        
        Args:
            new_level: New readiness level (1-4)
        
        Raises:
            ValueError: If new_level is invalid
        """
        if not isinstance(new_level, int):
            raise ValueError(
                f"readiness_level must be an integer, got {type(new_level).__name__}"
            )
        
        if not 1 <= new_level <= 4:
            raise ValueError(
                f"readiness_level must be between 1 and 4, got {new_level}"
            )
        
        self.readiness_level = new_level
    
    def mark_accessed(self) -> None:
        """Update last_accessed timestamp to current time."""
        self.last_accessed = datetime.now(timezone.utc)
