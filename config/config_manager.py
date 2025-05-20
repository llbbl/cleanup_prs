import os
import yaml
from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class KubernetesConfig:
    default_namespace: str
    context_required: bool

@dataclass
class HelmConfig:
    app_name_prefix: str
    days_threshold: int
    verification_sleep_seconds: int

@dataclass
class LoggingConfig:
    file_name: str
    directory: str
    rotation: Dict[str, Any]
    format: str

@dataclass
class Config:
    kubernetes: KubernetesConfig
    helm: HelmConfig
    logging: LoggingConfig

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config: Config = None

    def load_config(self, env: str = "default") -> Config:
        """Load configuration from YAML file."""
        config_path = self.config_dir / f"{env}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Validate and convert to Config object
        self.config = self._validate_and_convert(config_data)
        return self.config

    def _validate_and_convert(self, data: Dict[str, Any]) -> Config:
        """Validate configuration data and convert to Config object."""
        required_sections = ['kubernetes', 'helm', 'logging']
        for section in required_sections:
            if section not in data:
                raise ValueError(f"Missing required configuration section: {section}")

        # Convert and validate Kubernetes config
        k8s_data = data['kubernetes']
        kubernetes_config = KubernetesConfig(
            default_namespace=k8s_data.get('default_namespace', 'default'),
            context_required=k8s_data.get('context_required', True)
        )

        # Convert and validate Helm config
        helm_data = data['helm']
        helm_config = HelmConfig(
            app_name_prefix=helm_data.get('app_name_prefix', 'dev'),
            days_threshold=helm_data.get('days_threshold', 5),
            verification_sleep_seconds=helm_data.get('verification_sleep_seconds', 20)
        )

        # Convert and validate Logging config
        logging_data = data['logging']
        logging_config = LoggingConfig(
            file_name=logging_data.get('file_name', 'cleanup_old_releases.log'),
            directory=logging_data.get('directory', 'logs'),
            rotation=logging_data.get('rotation', {
                'when': 'W0',
                'interval': 1,
                'backup_count': 4
            }),
            format=logging_data.get('format', '%(asctime)s | %(levelname)s | %(message)s')
        )

        return Config(
            kubernetes=kubernetes_config,
            helm=helm_config,
            logging=logging_config
        )

    def get_config(self) -> Config:
        """Get the current configuration."""
        if self.config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self.config 