# Face Recognition with ArcFace ONNX and 5-Point Alignment

<img src="https://via.placeholder.com/800x200/007bff/ffffff?text=ArcFace+ONNX+%2B+5-Point+Alignment" alt="Project Banner" width="800"/>

**Author:** Gabriel Baziramwabo  
**Organization:** Benax Technologies Ltd · Rwanda Coding Academy  

This project implements a **practical, CPU-friendly face recognition pipeline** using:
- **ArcFace** model (exported to ONNX for cross-platform inference)
- **5-point facial landmark alignment** (eyes, nose, mouth corners)
- **Haar Cascade** + **MediaPipe FaceMesh** for detection and landmarks
- **Modular, testable stages** (no black-box end-to-end framework)

The system is designed to be understandable, debuggable, reproducible, and runnable on ordinary laptops without a GPU.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Pipeline Overview](#pipeline-overview)
- [Usage](#usage)
  - [1. Camera & Detection Validation](#1-camera--detection-validation)
  - [2. Enrollment](#2-enrollment)
  - [3. Threshold Evaluation](#3-threshold-evaluation)
  - [4. Live Recognition](#4-live-recognition)
- [Key Concepts](#key-concepts)
- [Troubleshooting](#troubleshooting)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Overview

This repository accompanies the book *"Face Recognition with ArcFace ONNX and 5-Point Alignment"*.

It demonstrates how to build a complete face recognition system from scratch — **not** just calling a pre-built library. Every stage is explicit and replaceable:

- Face detection → 5-point landmark detection → geometric alignment → embedding extraction → enrollment → cosine-similarity matching

The system emphasizes **CPU execution**, **reproducibility**, and **explainability** over maximum accuracy.

## Features

- CPU-only inference with ONNX Runtime
- 5-point alignment using left/right eye, nose tip, mouth corners
- Modular scripts — each file does one thing
- Automated project initialization (`init_project.py`)
- Enrollment with auto-capture and existing crop re-use
- Real-time multi-face recognition
- Threshold tuning based on genuine/impostor distances

## Project Structure

```text
face-recognition-5pt/
├── data/                 # Generated data (ignored in .gitignore)
│   ├── db/               # face_db.npz + face_db.json
│   └── enroll/           # per-person aligned 112×112 crops
├── models/
│   └── embedder_arcface.onnx     # ArcFace model (download separately)
├── src/
│   ├── camera.py         # Webcam test + FPS
│   ├── detect.py         # Haar face detection test
│   ├── landmarks.py      # 5-point landmark visualization
│   ├── align.py          # Alignment demo
│   ├── embed.py          # Embedding extraction + visualization
│   ├── enroll.py         # Enroll identities
│   ├── evaluate.py       # Threshold tuning
│   ├── haar_5pt.py       # Core: Haar + MediaPipe 5pt detector
│   └── recognize.py      # Real-time recognition
├── init_project.py       # Creates folder structure
├── README.md
└── .gitignore
