import re
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any, List, Pattern
from pathlib import Path

class TransactionType(Enum):
    FULIZA_USED = "FULIZA_USED"
    FULIZA_REPAYMENT = "FULIZA_REPAYMENT"
    RECEIVED = "RECEIVED"
    PAID = "PAID"
    SENT = "SENT"
    MSHWARI_WITHDRAWAL = "MSHWARI_WITHDRAWAL"
    MSHWARI_DEPOSIT = "MSHWARI_DEPOSIT"
    AIRTIME = "AIRTIME"
    WITHDRAW = "WITHDRAW"
    BALANCE_CHECK = "BALANCE_CHECK"

class TransactionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class MPESAParserError(Exception):
    """Base exception for MPESAMessageParser errors"""
    pass

class InvalidMessageError(MPESAParserError):
    """Raised when the message format is invalid"""
    pass

class NumericConversionError(MPESAParserError):
    """Raised when numeric conversion fails"""
    pass

@dataclass
class MPESATransaction:
    """Data class to hold parsed transaction details"""
    transaction_id: str
    transaction_type: TransactionType
    status: TransactionStatus
    amount: float
    mpesa_balance: Optional[float] = None
    mshwari_balance: Optional[float] = None
    transaction_cost: Optional[float] = None
    datetime: Optional[datetime] = None
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    recipient: Optional[str] = None
    recipient_phone: Optional[str] = None
    account_number: Optional[str] = None
    fuliza_interest: Optional[float] = None
    fuliza_total: Optional[float] = None
    fuliza_limit: Optional[float] = None
    fuliza_due_date: Optional[datetime] = None
    daily_limit: Optional[float] = None
    raw_message: str = ""

class DualMPESAParser:
    """
    Enhanced parser for M-PESA transaction messages in both English and Swahili
    with improved error handling, logging, and maintainability.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = self._setup_logger(log_level)
        self.patterns = self._compile_patterns()

    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Configure logging with proper formatting"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    def _compile_patterns(self) -> Dict[str, Pattern]:
        """Compile and store regex patterns"""
        base_patterns = {
            'ENGLISH': r"(?P<transaction_id>[A-Z0-9]{10})\s+[Cc]onfirmed\.?\s*",
            'SWAHILI': r"(?P<transaction_id>[A-Z0-9]{10})\s+Imethibitishwa\.?\s*"
        }
        
        transaction_patterns = {
            'ENGLISH': {
                'RECEIVED': r"You\shave\sreceived\sKsh(?P<received_amount>[\d,.]+)\sfrom\s(?P<sender_name>[^0-9]+?)(?:\s(?P<sender_phone>\d+))?",
                'PAID': r"Ksh(?P<paid_amount>[\d,.]+)\spaid\sto\s(?P<paid_to>[^.]+)",
                'SENT': r"Ksh(?P<sent_amount>[\d,.]+)\ssent\sto\s(?P<recipient>[^0-9]+?)(?:\sfor\saccount\s(?P<account_number>[^\s]+))?(?:\s(?P<recipient_phone>\d+))?",
                'MSHWARI': r"Ksh(?P<mshwari_amount>[\d,.]+)\stransferred\s(?P<mshwari_direction>(?:from|to))\sM-Shwari\saccount",
                'AIRTIME': r"You\sbought\sKsh(?P<airtime_amount>[\d,.]+)\sof\sairtime(?:\sfor\s(?P<airtime_phone>\d+))?",
                'WITHDRAW': r"(?:(?:on\s[^.]+?)?\s*Withdraw\s*Ksh(?P<withdraw_amount>[\d,.]+)\sfrom\s(?P<agent_details>[^.]+))",
                'BALANCE_CHECK': r"Your\saccount\sbalance\swas:\sM-PESA\sAccount\s:\sKsh(?P<balance_amount>[\d,.]+)"
            },
            'SWAHILI': {
                'KUTUMA': (
                    r"Ksh(?P<kutuma_amount>[\d,.]+)\s"
                    r"imetumwa\skwa\s"
                    r"(?P<kutuma_recipient>[^0-9]+?)\s"
                    r"(?P<kutuma_phone>\d{10})\s"
                    r"(?:tarehe|siku)\s"
                    r"(?P<kutuma_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<kutuma_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'KUPOKEA': (
                    r"Umepokea\sKsh(?P<kupokea_amount>[\d,.]+)\s"
                    r"kutoka\s"
                    r"(?P<kupokea_sender>[^0-9]+?)\s"
                    r"(?P<kupokea_phone>\d{10})\s"
                    r"mnamo\s"
                    r"(?P<kupokea_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<kupokea_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'SALIO': (
                    r"Baki\syako\sni:\s"
                    r"Akaunti\sya\sM-PESA\s:\s"
                    r"Ksh(?P<salio_amount>[\d,.]+)\s"
                    r"(?:Tarehe|tarehe)\s"
                    r"(?P<salio_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<salio_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'KULIPA_TILL': (
                    r"Umelipa\sKsh(?P<kulipa_amount>[\d,.]+)\s"
                    r"kwa\s(?P<kulipa_merchant>[^0-9]+?)\s"
                    r"(?P<kulipa_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"(?P<kulipa_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'DATA': (
                    r"Ksh(?P<data_amount>[\d,.]+)\s"
                    r"zimetumwa\skwa\sSAFARICOM\sDATA\sBUNDLES"
                    r"(?:\skwa\sakaunti\sSAFARICOM\sDATA\sBUNDLES)?\s"
                    r"mnamo\s"
                    r"(?P<data_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<data_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'MJAZO': (
                    r"Umenunua\sKsh(?P<mjazo_amount>[\d,.]+)\s"
                    r"ya\smjazo\s"
                    r"(?:siku|tarehe)\s"
                    r"(?P<mjazo_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<mjazo_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'PAYBILL': (
                    r"Ksh(?P<paybill_amount>[\d,.]+)\s"
                    r"imetumwa\skwa\s(?P<paybill_name>[^k]+?)\s"
                    r"kwa\sakaunti\snambari\s(?P<paybill_account>\d+)"
                ),
                'KUPOKEA_BANK': (
                    r"Umepokea\sKsh(?P<kupokea_bank_amount>[\d,.]+)\s"
                    r"kutoka\s(?P<kupokea_bank_name>[^0-9]+?)\s"
                    r"(?P<kupokea_bank_account>\d+)\s"
                    r"mnamo\s"
                    r"(?P<kupokea_bank_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<kupokea_bank_time>\d{1,2}:\d{2}\s*[AP]M)"
                ),
                'POCHI_LA_BIASHARA': (
                    r"Ksh(?P<pochi_amount>[\d,.]+)\s"
                    r"imetumwa\skwa\s"
                    r"(?P<pochi_recipient>[^0-9]+?)\s"
                    r"(?:tarehe|siku)\s"
                    r"(?P<pochi_date>\d{1,2}/\d{1,2}/\d{2})\s"
                    r"saa\s(?P<pochi_time>\d{1,2}:\d{2}\s*[AP]M)"
                )
            }
        }
        
        additional_patterns = {
            'mpesa_balance': r"Baki\s(?:yako|mpya)(?:\sya|\smpya\skatika|\skatika)\sM-PESA\sni\sKsh(?P<mpesa_balance>[\d,.]+)",
            'transaction_cost': r"Gharama\sya\s(?:kutuma|kununua|matumizi|kulipa)\sni\sKsh(?P<transaction_cost>[\d,.]+)",
            'daily_limit': r"Kiwango\scha\sPesa\sunachoweza\skutuma\skwa\ssiku\sni\s(?P<daily_limit>[\d,.]+)"
        }
        
        failed_patterns = {
            'ENGLISH': re.compile(
                r"Failed\.\s"
                r"(?:"
                r"(?:You\sdo\snot\shave\senough\smoney)|"
                r"(?:Insufficient\sfunds\sin\syour\sM-PESA\saccount)|"
                r"(?:You\shave\sinsufficient\sfunds)|"
                r"(?:Insufficient\sfunds\sin\syour\sM-PESA\saccount\sas\swell\sas\sFuliza\sM-PESA)|"
                r"(?:You\shave\sinsufficient\sfunds\sin\syour\sM-Shwari\saccount)|"
                r"(?:You\shave\sreached\syour\sFuliza\sM-PESA\slimit)|"
                r"(?:Your\sFuliza\sM-PESA\slimit\sis\snot\savailable\sat\sthis\stime)"
                r")"
            ),
            'SWAHILI': re.compile(
                r"(?:"
                r"Hakuna\spesa\sza\skutosha|"
                r"Imefeli|"
                r"Umekataa\skuidhinisha\samali|"
                r"Huduma\shi\shaipatikani"
                r")"
            )
        }
        
        compiled_patterns = {}
        for lang, base_pattern in base_patterns.items():
            transaction_part = '|'.join(
                f"(?P<{tx_type}>{pattern})"
                for tx_type, pattern in transaction_patterns[lang].items()
            )
            
            additional_part = ''.join(
                f"(?:.*?{pattern})?"
                for pattern in additional_patterns.values()
            )
            
            complete_pattern = (
                f"(?:{base_pattern})?"  # Made base pattern optional for failed transactions
                f"({transaction_part})"
                f"{additional_part}"
            )
            
            compiled_patterns[lang] = re.compile(complete_pattern, re.IGNORECASE | re.DOTALL)
        
        self.compiled_patterns = compiled_patterns
        self.failed_patterns = failed_patterns

    def clean_amount(self, amount_str: str) -> float:
        """Clean amount string and convert to float."""
        if not amount_str:
            return 0.0
        cleaned = amount_str.replace(',', '').replace(' ', '').strip().rstrip('.')
        return float(cleaned)

    def parse_message(self, message: str) -> Dict[str, any]:
        """Parse an M-PESA message and extract details."""
        if not isinstance(message, str):
            return {"error": "Message must be a string"}
        
        # Determine language
        lang = 'ENGLISH' if 'Confirmed' in message or 'confirmed' in message else 'SWAHILI'
        
        # Check for failed transaction
        failed_match = self.failed_patterns[lang].search(message)
        if failed_match:
            return {
                "status": "FAILED",
                "reason": failed_match.group(0),
                "original_message": message
            }
        
        # Match message against pattern
        match = self.compiled_patterns[lang].search(message)
        if not match:
            return {"error": "Message format not recognized"}
            
        result = {k: v for k, v in match.groupdict().items() if v is not None}
        
        # Clean up values
        for key in result:
            if isinstance(result[key], str):
                result[key] = result[key].strip()
        
        # Set transaction status
        result['status'] = 'SUCCESS'
        
        # Determine transaction type and clean amount
        for tx_type in self.transaction_patterns[lang].keys():
            if result.get(tx_type):
                result['transaction_type'] = tx_type
                amount_key = f"{tx_type.lower()}_amount"
                if amount_key in result:
                    result['amount'] = self.clean_amount(result[amount_key])
                    del result[amount_key]
                break
        
        # Clean numeric fields
        numeric_fields = {
            'mpesa_balance': 'mpesa_balance',
            'transaction_cost': 'transaction_cost',
            'daily_limit': 'daily_limit'
        }
        
        for eng_key, swa_key in numeric_fields.items():
            if eng_key in result:
                result[swa_key] = self.clean_amount(result[eng_key])
                del result[eng_key]
        
        # Parse date and time if present
        if 'date' in result and 'time' in result:
            try:
                datetime_str = f"{result['date']} {result['time']}"
                result['datetime'] = datetime.strptime(datetime_str, '%d/%m/%y %I:%M %p')
                del result['date']
                del result['time']
            except ValueError:
                pass
        
        return result

class MPESAMessageProcessor:
    """
    High-level processor for handling M-PESA messages with batch processing
    and result aggregation capabilities.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.parser = DualMPESAParser()
        if log_file:
            self.parser.logger.addHandler(self.setup_file_logger(log_file))
        
    def setup_file_logger(self, log_file: str):
        """Set up file logging"""
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
        )
        return file_handler

    def process_file(self, file_path: str) -> List[MPESATransaction]:
        """Process messages from a file"""
        results = []
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    transaction = self.parser.parse_message(line)
                    results.append(transaction)
                except MPESAParserError as e:
                    self.parser.logger.error(
                        f"Error processing line {line_num}: {str(e)}\n"
                        f"Message: {line}"
                    )
                    
        return results
        
    def generate_summary(self, transactions: List[MPESATransaction]) -> Dict[str, Any]:
        """Generate summary statistics from processed transactions"""
        summary = {
            'total_transactions': len(transactions),
            'successful_transactions': sum(
                1 for t in transactions 
                if t.status == TransactionStatus.SUCCESS
            ),
            'failed_transactions': sum(
                1 for t in transactions 
                if t.status == TransactionStatus.FAILED
            ),
            'transaction_types': {},
            'total_amount_processed': 0.0,
            'average_transaction_amount': 0.0,
            'total_transaction_costs': 0.0
        }
        
        # Collect transaction type statistics
        for transaction in transactions:
            t_type = transaction.transaction_type.value
            if t_type not in summary['transaction_types']:
                summary['transaction_types'][t_type] = 0
            summary['transaction_types'][t_type] += 1
            
            if transaction.status == TransactionStatus.SUCCESS:
                summary['total_amount_processed'] += transaction.amount
                if transaction.transaction_cost:
                    summary['total_transaction_costs'] += transaction.transaction_cost
                    
        if summary['successful_transactions'] > 0:
            summary['average_transaction_amount'] = (
                summary['total_amount_processed'] / 
                summary['successful_transactions']
            )
            
        return summary

def main():
    """Command line interface for the M-PESA message parser"""
    import argparse
    import json
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description='Process M-PESA transaction messages'
    )
    parser.add_argument(
        'input',
        help='Input file containing M-PESA messages (one per line)'
    )
    parser.add_argument(
        '--output',
        help='Output file for processed transactions (JSON format)'
    )
    parser.add_argument(
        '--log',
        help='Log file for processing details'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Generate and include summary statistics'
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = MPESAMessageProcessor(log_file=args.log)
    
    try:
        # Process messages
        transactions = processor.process_file(args.input)
        
        # Prepare output
        output_data = {
            'processed_at': datetime.now().isoformat(),
            'input_file': args.input,
            'transactions': [
                {
                    key: (value.value if isinstance(value, Enum) else
                          value.isoformat() if isinstance(value, datetime) else
                          value)
                    for key, value in vars(t).items()
                }
                for t in transactions
            ]
        }
        
        if args.summary:
            output_data['summary'] = processor.generate_summary(transactions)
            
        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
        else:
            print(json.dumps(output_data, indent=2))
            
    except Exception as e:
        processor.parser.logger.error(f"Processing failed: {str(e)}")
        raise

def interactive_mode():
    """Interactive mode for testing individual messages"""
    processor = MPESAMessageProcessor()
    
    print("M-PESA Message Parser Interactive Mode")
    print("Enter 'quit' or 'exit' to end the session\n")
    
    while True:
        try:
            message = input("\nEnter M-PESA message: ").strip()
            
            if message.lower() in ('quit', 'exit'):
                break
                
            if not message:
                print("Please enter a message")
                continue
                
            transaction = processor.parser.parse_message(message)
            
            print("\nParsed Transaction:")
            for key, value in vars(transaction).items():
                if value is not None and key != 'raw_message':
                    if isinstance(value, Enum):
                        value = value.value
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    print(f"{key}: {value}")
                    
        except MPESAParserError as e:
            print(f"\nError: {str(e)}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            
    print("\nGoodbye!")

if __name__ == "__main__":
    main()
