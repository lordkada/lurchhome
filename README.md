# 🏠 Lurch Home

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

> *“You rang?”* — **Lurch**, *The Addams Family*
>
> *The project name is an homage to Lurch, the Addams Family's iconic butler.*

**Lurch Home** is an advanced, open-source orchestration system designed to intelligently coordinate
domestic functions in a centralized and modular way.
The project integrates modern AI tools, neural models, and home automation technologies — creating a true smart assistant for your home.

---

## ⚠️ Disclaimer

This project is at a very early stage. Features, roadmap, and APIs may change rapidly as the project evolves and — since this is a spare‑time effort — progress will depend on the free time I can dedicate to it 🙂. Expect occasional breaking changes and incomplete components.

---

## 🚀 Project Overview

This project aims to build a "smart butler" capable of:

* Managing smart home devices via **Home Assistant**
* Interacting with users via a **Telegram Bot**
* Orchestrating multiple microservices with **OpenMCP**
* Coordinating conversations and goals using **Langchain**
* Maintaining shared conversation state through **Redis**
* Offering security features such as **image and facial recognition** using neural models

The system is designed to be modular, privacy-friendly, and extendable.

---

## 🧩 Architecture Components

| Component           | Description                                                                |
| ------------------- | -------------------------------------------------------------------------- |
| `Home Assistant`    | Home automation hub integration with existing registered devices           |
| `Telegram Bot`      | User-facing interface for interacting with the butler                      |
| `Langchain + Redis` | Handles context-aware conversations and memory between agents              |
| `OpenMCP`           | Orchestrates microservices and tools across the system                     |
| `AI Services`       | Specialized microservices for image/face recognition and security features |

---

## 🛠 Makefile Commands

Use the Makefile to simplify common tasks. Below are the most relevant targets:

### Setup & Project Init

```bash
make setup         # Create required folders and .env file from template
make build         # Build services using docker-compose
make up            # Start services in detached mode
make down          # Stop all services
make restart       # Restart all running services
make logs          # Tail logs from all services
make logs-ha       # Tail logs from Home Assistant only
make status        # Show running containers
```

### Maintenance

```bash
make clean         # Stop containers and remove volumes/images
make backup        # Create a backup archive of volumes
make restore BACKUP_FILE=path/to/backup.tar.gz  # Restore from a backup
```

### Development & Testing

```bash
make install       # Install Python dependencies with pipenv
make install-dev   # Install dev dependencies
make shell         # Open a pipenv shell
make test          # Run tests with pytest
make lint          # Run flake8 and black checks
make format        # Autoformat code using black
make run           # Run main application
```

### 📦 Project Structure (WIP)

```text
├── docker/
│   └── volumes/
│       └── homeassistant/
├── src/
│   └── integrations/
│       └── home_assistant_connector.py
│   └── main.py
├── tests/
├── .env.example
├── Makefile
├── README.md
```

## 📜 License

This project is licensed under the Apache License 2.0.
You are free to use, modify, distribute, and integrate this software — even in commercial settings — as long as you respect the terms of the license.
For more information, see the [LICENSE](LICENSE) file.

## 🤝 Contributions

Feel free to fork, clone, open issues, or submit PRs. The goal is to build a practical and modular home AI assistant that remains transparent and privacy-conscious.

---

Developed with ❤️ by Lord KADA.
