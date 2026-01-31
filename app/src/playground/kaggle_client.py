""" app/src/playground/kaggle_client.py

Kaggle Kernel Server Controller. Mounts kernel onto local Jupyter environment for dataset access
"""

import json
import subprocess
from pathlib import Path
from typing import Literal
from kaggle.api.kaggle_api_extended import KaggleApi
from pydantic import BaseModel, Field, ConfigDict, field_validator

from ... import workspace
from ...utils.woodlogs import setup_logger

logger = setup_logger(__name__)

# Remote Kaggle directories
KAGGLE_WORKING_DIR = "/kaggle/working/"
KAGGLE_INPUT_DIR = "/kaggle/input/"

class KaggleKernelMetadata(BaseModel):
    """ Kaggle Metadata for creating and managing kernels via API. """

    model_config = ConfigDict(
        # Allow arbitrary types if needed
        arbitrary_types_allowed=True,
        # Use enum values instead of names
        use_enum_values=True,
    )
    username: str = Field(..., description="Kaggle username")
    title: str = Field(..., description="Kernel title")
    code_file_path: Path = Field(..., description="Local path to notebook or script file")
    language: Literal["python", "r", "rmarkdown"] = Field(
        default="python", description="Programming language"
    )
    kernel_type: Literal["script", "notebook"] = Field(
        default="notebook", description="Kernel type"
    )
    is_private: bool = Field(default=True, description="Whether kernel is private")
    enable_gpu: bool = Field(default=False, description="Enable GPU")
    enable_tpu: bool = Field(default=False, description="Enable TPU")
    enable_internet: bool = Field(default=True, description="Enable internet access")
    dataset_sources: list[str] = Field(default_factory=list, description="Dataset sources")
    competition_sources: list[str] = Field(default_factory=list, description="Competition sources")
    kernel_sources: list[str] = Field(default_factory=list, description="Kernel sources")
    model_sources: list[str] = Field(default_factory=list, description="Model sources")
    # sessionId: uuid.UUID = Field(default_factory=uuid.uuid4, description="Session ID")

    @property
    def kernel_id(self) -> str:
        return f"{self.username}/{self.title}"

    @field_validator("code_file_path", mode="before")
    @classmethod
    def validate_code_file(cls, v: str) -> str:
        """Ensure code_file_path ends with appropriate extension."""
        path = Path(v)
        valid_extensions = {".ipynb", ".py", ".r", ".Rmd"}
        if path.suffix not in valid_extensions:
            raise ValueError(
                f"code_file_path must have one of {valid_extensions}, got {path.suffix}"
            )
        return v

    def kaggle_metadata_json(self) -> dict:
        """
        Dump model as Kaggle kernel-metadata.json format.
        Matches exact schema expected by `kaggle kernels push`.
        """

        return {
            "id": self.kernel_id,
            "title": self.title,
            "code_file": str(self.code_file_path),  # Just filename, not full path
            "language": self.language,
            "kernel_type": self.kernel_type,
            "is_private": self.is_private,
            "enable_gpu": self.enable_gpu,
            "enable_tpu": self.enable_tpu,
            "enable_internet": self.enable_internet,
            "dataset_sources": self.dataset_sources,
            "competition_sources": self.competition_sources,
            "kernel_sources": self.kernel_sources,
            "model_sources": self.model_sources,
        }

    def save_metadata_file(self):
        """Get path to kernel-metadata.json file."""
        filepath = self.code_file_path.parent / "kernel-metadata.json"

        with open(filepath, "w") as f:
            json.dump(self.kaggle_metadata_json(), f, indent=2)

        logger.info(f"Saved metadata to {filepath}")

class KaggleKernelManager:
    """ Kaggle kernels via API Controller. """

    def __init__(self, root_path: Path = workspace.dir.app_path):
        # Kaggle API Client
        self.api = KaggleApi()
        self.api.authenticate()
        self.root_path = root_path
        self.on_start()
        logger.info(f"KaggleKernelManager initialized with workspace {self.workspace_dir}")

    def on_start(self):
        self.workspace_dir = self.root_path / "tmp" / "kaggle_kernels"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def username(self) -> str:
        return self.api.config_values.get("username", "unknown")

    def create_kernel(
        self,
        kernel_name: str,
        **kwargs
    ):
        """
        Create a new disposable Kaggle kernel from a notebook file.

        Args:
            kernel_name: Name of the kernel to create.
            **kwargs: Additional metadata fields for KaggleKernelMetadata.

        Returns: KaggleKernelMetadata
        """

        kernel_dir = self.workspace_dir / kernel_name
        kernel_dir.mkdir(parents=True, exist_ok=True)
        script_path = self.create_python_script(
            script_content=kwargs.get("script_content", "from pathlib import Path\nprint(Path('kaggle/inputs').iterdir())"),
            file_path=kernel_dir / "script.py",
        )
        metadata = KaggleKernelMetadata(username=self.username, title=kernel_name, code_file_path=script_path, **kwargs)  # Validate metadata
        metadata.save_metadata_file()
        self.execute_kernel_kaggle(kernel_dir)

        return metadata

    def execute_kernel_kaggle(self, local_kernel_path: Path):
        """
        Execute a Kaggle kernel located at local_kernel_path.
        """
        cmd = ["kaggle", "kernels", "push", "-p", str(local_kernel_path)]
        logger.info(f"Executing kernel: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to execute kernel: {result}")

        logger.info(f"Successfully executed kernel at: {local_kernel_path}")

    def create_python_script(
        self,
        file_path: Path,
        script_content: str,
    ):
        """
        Create a Python script file in the workspace.

        Returns: Path to the created script file.
        """
        with open(file_path, "w") as f:
            f.write(script_content)

        logger.info(f"Created Python script at: {file_path}")

        return file_path

    def check_kernel_status(self, kernel_name: str):
        """ Check the status of a Kaggle kernel by slug e.g. kaggle-username/kernel-name. """

        output = self.api.kernels_status(kernel_name)
        logger.info(f"Kernel status for {kernel_name}: {output}")

    def get_kernel_output(self, kernel_config: KaggleKernelMetadata):

        output = self.api.kernels_output(
            kernel_config.kernel_id,
            path=kernel_config.code_file_path.name,
        )
        logger.info(f"Kernel output for {kernel_config.kernel_id}: {output}")
        return output

if __name__ == "__main__":

    DEFAULT_CODE_CONTENT = """
    import pandas as pd
    import os

    # List available datasets
    print("Available datasets in /kaggle/input/:")
    for item in os.listdir("/kaggle/input/"):
        print(f"  - {item}")
        if os.path.isdir(f"/kaggle/input/{item}"):
            print(f"    Files: {os.listdir(f'/kaggle/input/{item}')}")

    # Load Titanic data from competition
    train_df = pd.read_csv("/kaggle/input/titanic/train.csv")
    test_df = pd.read_csv("/kaggle/input/titanic/test.csv")

    print(f"\\nTrain shape: {train_df.shape}")
    print(f"Test shape: {test_df.shape}")
    print(f"\\nTrain columns: {list(train_df.columns)}")
    print(f"\\nFirst 5 rows:\\n{train_df.head()}")

    # Basic analysis
    survival_rate = train_df['Survived'].mean()
    print(f"\\nOverall survival rate: {survival_rate:.2%}")

    # Save results
    train_df.describe().to_csv("/kaggle/working/train_statistics.csv")
    print("\\n✅ Saved train_statistics.csv")
    """

    manager = KaggleKernelManager()
    meta = manager.create_kernel(
        kernel_name="test-kernel-2",
        language="python",
        kernel_type="script",
        dataset_sources=["heptapod/titanic"],
        is_private=True,
        enable_gpu=False,
        enable_internet=True,
        script_content=DEFAULT_CODE_CONTENT,
    )
    logger.info(f"Created and executed kernel: {meta.kernel_id}")

    output = manager.get_kernel_output(meta)
    manager.api.kernels_delete(meta.kernel_id, no_confirm=True)