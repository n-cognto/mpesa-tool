# M-PESA Message Parser

## Overview

The M-PESA Message Parser is a tool designed to parse and extract details from M-PESA transaction messages. It supports both English and Swahili messages, providing enhanced error handling, logging, and maintainability.

## Features

- Supports parsing of various M-PESA transaction types including:
  - Fuliza M-PESA usage and repayment
  - Received money
  - Sent money
  - M-Shwari transactions
  - Airtime purchases
  - Withdrawals
  - Balance checks
- Handles both successful and failed transactions
- Provides detailed logging for error tracking
- Batch processing of messages from a file
- Generates summary statistics from processed transactions

## Installation

To use the M-PESA Message Parser, ensure you have Python installed on your system. Clone the repository and navigate to the project directory.

```bash
git clone <repository-url>
cd <repository-directory>
```

## Usage

### Command Line Interface

The tool can be used via the command line to process M-PESA messages from a file and optionally generate a summary.

```bash
python refined_test.py <input-file> [--output <output-file>] [--log <log-file>] [--summary]
```

- `<input-file>`: Path to the input file containing M-PESA messages (one per line).
- `--output <output-file>`: (Optional) Path to the output file for processed transactions (JSON format).
- `--log <log-file>`: (Optional) Path to the log file for processing details.
- `--summary`: (Optional) Generate and include summary statistics.

### Example

```bash
python refined_test.py messages.txt --output results.json --log process.log --summary
```

### Interactive Mode

The tool also provides an interactive mode for testing individual messages.

```bash
python refined_test.py
```

In interactive mode, you can enter M-PESA messages one by one and see the parsed results. Type 'exit' to quit the session.

## Output

The output JSON file contains the following information:

- `processed_at`: Timestamp of when the processing was done.
- `input_file`: Path to the input file.
- `transactions`: List of parsed transactions with details such as transaction ID, type, status, amount, balances, and more.
- `summary` (if `--summary` is used): Summary statistics including total transactions, successful and failed transactions, transaction types, total amount processed, average transaction amount, and total transaction costs.

## Logging

The tool logs detailed processing information, including errors, to the specified log file. This helps in tracking and debugging issues during message parsing.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For any questions or support, please contact [your-email@example.com].
