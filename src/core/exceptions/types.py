from pydantic import BaseModel
from pydantic.dataclasses import dataclass

class ErrorCategory(BaseModel):
    @dataclass
    class DomainError:
        BUSINESS_RULE_VIOLATION: str = "DomainError.BUSINESS_RULE_VIOLATION"
        INVARIANT_VIOLATION: str = "DomainError.INVARIANT_VIOLATION"
        DOMAIN_CONSTRAINT_VIOLATION: str = "DomainError.DOMAIN_CONSTRAINT_VIOLATION"
        AGGREGATE_STATE_INVALID: str = "DomainError.AGGREGATE_STATE_INVALID"
        DOMAIN_EVENT_PROCESSING_ERROR: str = "DomainError.DOMAIN_EVENT_PROCESSING_ERROR"
        VALUE_OBJECT_CREATION_ERROR: str = "DomainError.VALUE_OBJECT_CREATION_ERROR"

    @dataclass
    class ApplicationError:
        VALIDATION_ERROR: str = "ApplicationError.VALIDATION_ERROR"
        COMMAND_HANDLING_ERROR: str = "ApplicationError.COMMAND_HANDLING_ERROR"
        QUERY_HANDLING_ERROR: str = "ApplicationError.QUERY_HANDLING_ERROR"
        USE_CASE_EXECUTION_ERROR: str = "ApplicationError.USE_CASE_EXECUTION_ERROR"
        MAPPING_ERROR: str = "ApplicationError.MAPPING_ERROR"
        WORKFLOW_ERROR: str = "ApplicationError.WORKFLOW_ERROR"
        NOTIFICATION_ERROR: str = "ApplicationError.NOTIFICATION_ERROR"

    @dataclass
    class DatabaseError:
        CONNECTION_ERROR: str = "DatabaseError.CONNECTION_ERROR"
        QUERY_EXECUTION_ERROR: str = "DatabaseError.QUERY_EXECUTION_ERROR"
        TRANSACTION_ERROR: str = "DatabaseError.TRANSACTION_ERROR"
        MIGRATION_ERROR: str = "DatabaseError.MIGRATION_ERROR"
        CONSTRAINT_VIOLATION: str = "DatabaseError.CONSTRAINT_VIOLATION"
        DEADLOCK_ERROR: str = "DatabaseError.DEADLOCK_ERROR"
        TIMEOUT_ERROR: str = "DatabaseError.TIMEOUT_ERROR"

    @dataclass
    class ExternalServiceError:
        SERVICE_UNAVAILABLE: str = "ExternalServiceError.SERVICE_UNAVAILABLE"
        SERVICE_TIMEOUT: str = "ExternalServiceError.SERVICE_TIMEOUT"
        API_LIMIT_EXCEEDED: str = "ExternalServiceError.API_LIMIT_EXCEEDED"
        INVALID_RESPONSE: str = "ExternalServiceError.INVALID_RESPONSE"
        SERVICE_AUTHENTICATION: str = "ExternalServiceError.SERVICE_AUTHENTICATION"
        THIRD_PARTY_ERROR: str = "ExternalServiceError.THIRD_PARTY_ERROR"

    @dataclass
    class FileSystemError:
        FILE_NOT_FOUND: str = "FileSystemError.FILE_NOT_FOUND"
        FILE_ACCESS_DENIED: str = "FileSystemError.FILE_ACCESS_DENIED"
        DISK_SPACE_ERROR: str = "FileSystemError.DISK_SPACE_ERROR"
        FILE_CORRUPTED: str = "FileSystemError.FILE_CORRUPTED"
        DIRECTORY_ERROR: str = "FileSystemError.DIRECTORY_ERROR"

    @dataclass
    class ConfigurationError:
        CONFIGURATION_MISSING: str = "ConfigurationError.CONFIGURATION_MISSING"
        INVALID_CONFIGURATION: str = "ConfigurationError.INVALID_CONFIGURATION"
        ENVIRONMENT_ERROR: str = "ConfigurationError.ENVIRONMENT_ERROR"
        SECRET_ACCESS_ERROR: str = "ConfigurationError.SECRET_ACCESS_ERROR"

    @dataclass
    class CacheError:
        CACHE_CONNECTION_ERROR: str = "CacheError.CACHE_CONNECTION_ERROR"
        CACHE_TIMEOUT: str = "CacheError.CACHE_TIMEOUT"
        CACHE_INVALIDATION: str = "CacheError.CACHE_INVALIDATION"
        CACHE_SERIALIZATION_ERROR: str = "CacheError.CACHE_SERIALIZATION_ERROR"

    @dataclass
    class MessagingError:
        MESSAGE_PUBLISH_ERROR: str = "MessagingError.MESSAGE_PUBLISH_ERROR"
        MESSAGE_CONSUMPTION_ERROR: str = "MessagingError.MESSAGE_CONSUMPTION_ERROR"
        CONNECTION_CLOSED_ERROR: str = "MessagingError.CONNECTION_CLOSED_ERROR"
        MESSAGE_SERIALIZATION_ERROR: str = "MessagingError.MESSAGE_SERIALIZATION_ERROR"

    @dataclass
    class SecurityError:
        AUTHENTICATION_FAILED: str = "SecurityError.AUTHENTICATION_FAILED"
        AUTHORIZATION_DENIED: str = "SecurityError.AUTHORIZATION_DENIED"
        PERMISSION_DENIED: str = "SecurityError.PERMISSION_DENIED"
        TOKEN_EXPIRED: str = "SecurityError.TOKEN_EXPIRED"
        TOKEN_INVALID: str = "SecurityError.TOKEN_INVALID"
        SESSION_EXPIRED: str = "SecurityError.SESSION_EXPIRED"
        TWO_FACTOR_AUTH_REQUIRED: str = "SecurityError.TWO_FACTOR_AUTH_REQUIRED"
        ACCOUNT_LOCKED: str = "SecurityError.ACCOUNT_LOCKED"
        PASSWORD_POLICY_VIOLATION: str = "SecurityError.PASSWORD_POLICY_VIOLATION"
        SUSPICIOUS_ACTIVITY: str = "SecurityError.SUSPICIOUS_ACTIVITY"
        RATE_LIMIT_EXCEEDED: str = "SecurityError.RATE_LIMIT_EXCEEDED"
        CSRF_TOKEN_INVALID: str = "SecurityError.CSRF_TOKEN_INVALID"

    @dataclass
    class NetworkError:
        CONNECTION_TIMEOUT: str = "NetworkError.CONNECTION_TIMEOUT"
        CONNECTION_REFUSED: str = "NetworkError.CONNECTION_REFUSED"
        NETWORK_UNREACHABLE: str = "NetworkError.NETWORK_UNREACHABLE"
        DNS_RESOLUTION_ERROR: str = "NetworkError.DNS_RESOLUTION_ERROR"
        SSL_HANDSHAKE_ERROR: str = "NetworkError.SSL_HANDSHAKE_ERROR"
        PROXY_ERROR: str = "NetworkError.PROXY_ERROR"
        BANDWIDTH_LIMIT_EXCEEDED: str = "NetworkError.BANDWIDTH_LIMIT_EXCEEDED"

    @dataclass
    class SystemError:
        OUT_OF_MEMORY_ERROR: str = "SystemError.OUT_OF_MEMORY_ERROR"
        CONCURRENCY_ERROR: str = "SystemError.CONCURRENCY_ERROR"
        DEADLOCK_DETECTED: str = "SystemError.DEADLOCK_DETECTED"
        RESOURCE_EXHAUSTED: str = "SystemError.RESOURCE_EXHAUSTED"
        THREAD_POOL_EXHAUSTED: str = "SystemError.THREAD_POOL_EXHAUSTED"
        STACK_OVERFLOW_ERROR: str = "SystemError.STACK_OVERFLOW_ERROR"
        GARBAGE_COLLECTION_ERROR: str = "SystemError.GARBAGE_COLLECTION_ERROR"
        SYSTEM_RESOURCE_ERROR: str = "SystemError.SYSTEM_RESOURCE_ERROR"
        PROCESS_KILLED: str = "SystemError.PROCESS_KILLED"
        UNEXPECTED_SHUTDOWN: str = "SystemError.UNEXPECTED_SHUTDOWN"
        RUNTIME_ERROR: str = "SystemError.RUNTIME_ERROR"

    @dataclass
    class UnknownError:
        UNCLASSIFIED_ERROR: str = "UnknownError.UNCLASSIFIED_ERROR"
        LEGACY_ERROR: str = "UnknownError.LEGACY_ERROR"
        THIRD_PARTY_UNKNOWN_ERROR: str = "UnknownError.THIRD_PARTY_UNKNOWN_ERROR"