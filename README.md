# LLM-OCR-SWPC

This repository contains the code and data for the paper "LLM-OCR-SWPC". It evaluates the performance of Large Language Models (InternVL series) on OCR tasks across different languages (English, Chinese, Japanese).

## Project Structure

The project is organized as follows:

```
LLM-OCR-SWPC/
├── data/
│   ├── raw/                # Raw images used for OCR
│   └── ground_truth/       # Manual ground truth text
├── results/                # Experiment results (CSV, Excel, Text outputs)
├── figures/                # Generated plots and figures
├── paper/                  # LaTeX source for the paper
├── notebooks/              # Jupyter notebooks for experiments and analysis
├── src/                    # Source code (if any extracted)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jpcosta90/LLM-OCR-SWPC.git
   cd LLM-OCR-SWPC
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The main experiment and analysis are contained in the Jupyter Notebook: `notebooks/LLM-OCR-SWPC.ipynb`.

To run the notebook:
1. Start Jupyter Notebook or Lab:
   ```bash
   jupyter notebook
   ```
2. Open `notebooks/LLM-OCR-SWPC.ipynb`.
3. Run the cells to reproduce the experiments and generate the figures.

## Data

- **Images**: Located in `data/raw/`. Includes `english.jpeg`, `chinese.jpeg`, `japanese.jpeg`.
- **Ground Truth**: Located in `data/ground_truth/manual_ocr_ground_truth.csv`.

## Results

The results of the experiments are saved in `results/`.
- `ocr_models_comparison_results.csv`: Detailed results for each round.
- `ocr_statistics_report.xlsx`: Summary statistics.
- `ocr_outputs_experiment/`: Raw text outputs from the models.

## License

[Insert License Here]
