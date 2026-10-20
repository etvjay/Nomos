// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @title Nomos Custody Vault
/// @notice Holds a test asset and enforces proposal-bound custody intents.
///         Authorization is restricted to the configured GenLayer authorizer;
///         settlement is permissionless but can only execute the exact stored
///         token, recipient, and amount.
contract NomosCustodyVault {
    struct Intent {
        bool exists;
        string status;
        string reasonCode;
        address token;
        address recipient;
        uint256 amount;
        uint256 authorizedAt;
        uint256 expiresAt;
        uint256 settledAt;
        uint256 attempts;
        address settler;
        uint256 custodyBefore;
        uint256 custodyAfter;
        uint256 recipientBefore;
        uint256 recipientAfter;
    }

    address public owner;
    address public authorizer;
    bool public paused;
    uint256 private _locked;

    mapping(address => bool) public allowedTokens;
    mapping(bytes32 => Intent) private _intents;

    event Authorized(
        bytes32 indexed key,
        string proposalId,
        address indexed token,
        address indexed recipient,
        uint256 amount,
        uint256 expiresAt
    );
    event AuthorizationRefused(bytes32 indexed key, string proposalId, string reasonCode);
    event Settled(
        bytes32 indexed key,
        string proposalId,
        address indexed token,
        address indexed recipient,
        uint256 amount,
        uint256 custodyBefore,
        uint256 custodyAfter,
        uint256 recipientBefore,
        uint256 recipientAfter,
        address settler
    );
    event SettlementRefused(
        bytes32 indexed key,
        string proposalId,
        string reasonCode,
        uint256 custodyBalance
    );
    event Deposited(address indexed from, address indexed token, uint256 amount, uint256 beforeBalance, uint256 afterBalance);
    event EmergencyWithdraw(address indexed token, address indexed to, uint256 amount, uint256 beforeBalance, uint256 afterBalance);
    event AuthorizerChanged(address indexed previousAuthorizer, address indexed nextAuthorizer);
    event TokenAllowed(address indexed token, bool allowed);
    event PausedChanged(bool paused, address indexed account);
    event OwnershipTransferred(address indexed previousOwner, address indexed nextOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "VAULT_NOT_OWNER");
        _;
    }

    modifier onlyAuthorizer() {
        require(msg.sender == authorizer, "VAULT_CALLER_NOT_AUTHORIZER");
        _;
    }

    modifier nonReentrant() {
        require(_locked == 0, "VAULT_REENTRANT");
        _locked = 1;
        _;
        _locked = 0;
    }

    constructor(address initialAuthorizer, address token) {
        require(initialAuthorizer != address(0), "VAULT_INVALID_AUTHORIZER");
        require(token != address(0), "VAULT_INVALID_TOKEN");
        owner = msg.sender;
        authorizer = initialAuthorizer;
        allowedTokens[token] = true;
        emit OwnershipTransferred(address(0), msg.sender);
        emit AuthorizerChanged(address(0), initialAuthorizer);
        emit TokenAllowed(token, true);
    }

    receive() external payable {
        revert("VAULT_NO_ETH");
    }

    function _key(string calldata proposalId) internal pure returns (bytes32) {
        return keccak256(bytes(proposalId));
    }

    function _eq(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }

    /// @notice Create the exact intent for a Core-bound proposal. Only the
    ///         authorizer may call this. A prior REFUSED record may be replaced;
    ///         AUTHORIZED/SETTLED/EXPIRED records are never overwritten.
    function authorize(
        string calldata proposalId,
        address token,
        address recipient,
        uint256 amount,
        uint256 expiresAt
    ) external onlyAuthorizer nonReentrant returns (bool ok, string memory reasonCode) {
        bytes32 key = _key(proposalId);
        Intent storage it = _intents[key];

        if (it.exists) {
            if (_eq(it.status, "AUTHORIZED")) {
                emit AuthorizationRefused(key, proposalId, "VAULT_INTENT_EXISTS");
                return (false, "VAULT_INTENT_EXISTS");
            }
            if (_eq(it.status, "SETTLED")) {
                emit AuthorizationRefused(key, proposalId, "VAULT_INTENT_ALREADY_SETTLED");
                return (false, "VAULT_INTENT_ALREADY_SETTLED");
            }
            if (_eq(it.status, "EXPIRED")) {
                emit AuthorizationRefused(key, proposalId, "VAULT_INTENT_EXPIRED");
                return (false, "VAULT_INTENT_EXPIRED");
            }
        }

        if (paused) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_PAUSED", token, recipient, amount, expiresAt);
        }
        if (!allowedTokens[token]) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_TOKEN_NOT_ALLOWED", token, recipient, amount, expiresAt);
        }
        if (bytes(proposalId).length == 0) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_INVALID_PROPOSAL_ID", token, recipient, amount, expiresAt);
        }
        if (recipient == address(0)) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_INVALID_RECIPIENT", token, recipient, amount, expiresAt);
        }
        if (amount == 0) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_INVALID_AMOUNT", token, recipient, amount, expiresAt);
        }
        if (expiresAt <= block.timestamp) {
            return _refuseAuthorization(key, proposalId, it, "VAULT_INVALID_EXPIRY", token, recipient, amount, expiresAt);
        }

        it.exists = true;
        it.status = "AUTHORIZED";
        it.reasonCode = "";
        it.token = token;
        it.recipient = recipient;
        it.amount = amount;
        it.authorizedAt = block.timestamp;
        it.expiresAt = expiresAt;
        it.settledAt = 0;
        it.attempts = 0;
        it.settler = address(0);
        it.custodyBefore = 0;
        it.custodyAfter = 0;
        it.recipientBefore = 0;
        it.recipientAfter = 0;

        emit Authorized(key, proposalId, token, recipient, amount, expiresAt);
        return (true, "");
    }

    function _refuseAuthorization(
        bytes32 key,
        string calldata proposalId,
        Intent storage it,
        string memory reason,
        address token,
        address recipient,
        uint256 amount,
        uint256 expiresAt
    ) internal returns (bool, string memory) {
        it.exists = true;
        it.status = "REFUSED";
        it.reasonCode = reason;
        it.token = token;
        it.recipient = recipient;
        it.amount = amount;
        it.authorizedAt = block.timestamp;
        it.expiresAt = expiresAt;
        emit AuthorizationRefused(key, proposalId, reason);
        return (false, reason);
    }

    /// @notice Execute an already-authorized intent. Permissionless by design:
    ///         the caller cannot change token, recipient, or amount.
    function settle(
        string calldata proposalId,
        address token,
        address recipient,
        uint256 amount
    ) external nonReentrant returns (bool ok, string memory reasonCode) {
        bytes32 key = _key(proposalId);
        Intent storage it = _intents[key];

        if (!it.exists) {
            emit SettlementRefused(key, proposalId, "VAULT_INTENT_NOT_FOUND", 0);
            return (false, "VAULT_INTENT_NOT_FOUND");
        }

        uint256 custodyBalance = IERC20(it.token).balanceOf(address(this));

        if (_eq(it.status, "SETTLED")) {
            return _refuseSettlement(key, proposalId, it, "VAULT_INTENT_ALREADY_SETTLED", custodyBalance);
        }
        if (_eq(it.status, "EXPIRED")) {
            return _refuseSettlement(key, proposalId, it, "VAULT_INTENT_EXPIRED", custodyBalance);
        }
        if (paused) {
            return _refuseSettlement(key, proposalId, it, "VAULT_PAUSED", custodyBalance);
        }
        if (!allowedTokens[it.token]) {
            return _refuseSettlement(key, proposalId, it, "VAULT_TOKEN_NOT_ALLOWED", custodyBalance);
        }
        if (token != it.token) {
            return _refuseSettlement(key, proposalId, it, "VAULT_TOKEN_MISMATCH", custodyBalance);
        }
        if (recipient != it.recipient) {
            return _refuseSettlement(key, proposalId, it, "VAULT_RECIPIENT_MISMATCH", custodyBalance);
        }
        if (amount != it.amount) {
            return _refuseSettlement(key, proposalId, it, "VAULT_AMOUNT_MISMATCH", custodyBalance);
        }
        if (block.timestamp >= it.expiresAt) {
            it.status = "EXPIRED";
            it.reasonCode = "VAULT_INTENT_EXPIRED";
            it.attempts += 1;
            emit SettlementRefused(key, proposalId, "VAULT_INTENT_EXPIRED", custodyBalance);
            return (false, "VAULT_INTENT_EXPIRED");
        }
        if (_eq(it.status, "REFUSED")) {
            return _refuseSettlement(key, proposalId, it, "VAULT_INTENT_NOT_AUTHORIZED", custodyBalance);
        }
        if (custodyBalance < it.amount) {
            return _refuseSettlement(key, proposalId, it, "VAULT_INSUFFICIENT_CUSTODY", custodyBalance);
        }

        address tokenAddr = it.token;
        address recipientAddr = it.recipient;
        uint256 amountToSend = it.amount;
        uint256 recipientBefore = IERC20(tokenAddr).balanceOf(recipientAddr);

        it.custodyBefore = custodyBalance;
        it.recipientBefore = recipientBefore;

        try IERC20(tokenAddr).transfer(recipientAddr, amountToSend) returns (bool success) {
            if (!success) {
                return _refuseSettlement(key, proposalId, it, "VAULT_TRANSFER_FAILED", custodyBalance);
            }
        } catch {
            return _refuseSettlement(key, proposalId, it, "VAULT_TRANSFER_FAILED", custodyBalance);
        }

        it.attempts += 1;
        it.status = "SETTLED";
        it.reasonCode = "";
        it.settledAt = block.timestamp;
        it.settler = msg.sender;
        it.custodyAfter = IERC20(tokenAddr).balanceOf(address(this));
        it.recipientAfter = IERC20(tokenAddr).balanceOf(recipientAddr);

        emit Settled(
            key,
            proposalId,
            tokenAddr,
            recipientAddr,
            amountToSend,
            it.custodyBefore,
            it.custodyAfter,
            it.recipientBefore,
            it.recipientAfter,
            msg.sender
        );
        return (true, "");
    }

    function _refuseSettlement(
        bytes32 key,
        string calldata proposalId,
        Intent storage it,
        string memory reason,
        uint256 custodyBalance
    ) internal returns (bool, string memory) {
        it.reasonCode = reason;
        it.attempts += 1;
        emit SettlementRefused(key, proposalId, reason, custodyBalance);
        return (false, reason);
    }

    function deposit(address token, uint256 amount) external nonReentrant {
        require(allowedTokens[token], "VAULT_TOKEN_NOT_ALLOWED");
        require(amount > 0, "VAULT_INVALID_AMOUNT");
        uint256 beforeBalance = IERC20(token).balanceOf(address(this));
        require(IERC20(token).transferFrom(msg.sender, address(this), amount), "VAULT_TRANSFER_FAILED");
        uint256 afterBalance = IERC20(token).balanceOf(address(this));
        emit Deposited(msg.sender, token, amount, beforeBalance, afterBalance);
    }

    function withdraw(address token, address to, uint256 amount) external onlyOwner nonReentrant {
        require(allowedTokens[token], "VAULT_TOKEN_NOT_ALLOWED");
        require(to != address(0), "VAULT_INVALID_RECIPIENT");
        require(amount > 0, "VAULT_INVALID_AMOUNT");
        uint256 beforeBalance = IERC20(token).balanceOf(address(this));
        require(beforeBalance >= amount, "VAULT_INSUFFICIENT_CUSTODY");
        require(IERC20(token).transfer(to, amount), "VAULT_TRANSFER_FAILED");
        emit EmergencyWithdraw(token, to, amount, beforeBalance, beforeBalance - amount);
    }

    function setAuthorizer(address nextAuthorizer) external onlyOwner {
        require(nextAuthorizer != address(0), "VAULT_INVALID_AUTHORIZER");
        emit AuthorizerChanged(authorizer, nextAuthorizer);
        authorizer = nextAuthorizer;
    }

    function setPaused(bool value) external onlyOwner {
        paused = value;
        emit PausedChanged(value, msg.sender);
    }

    function allowToken(address token, bool allowed) external onlyOwner {
        require(token != address(0), "VAULT_INVALID_TOKEN");
        allowedTokens[token] = allowed;
        emit TokenAllowed(token, allowed);
    }

    function transferOwnership(address nextOwner) external onlyOwner {
        require(nextOwner != address(0), "VAULT_INVALID_OWNER");
        emit OwnershipTransferred(owner, nextOwner);
        owner = nextOwner;
    }

    function getSettlement(string calldata proposalId) external view returns (Intent memory) {
        return _intents[_key(proposalId)];
    }

    function custodyBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
}
