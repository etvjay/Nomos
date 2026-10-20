// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Nomos Test Asset
/// @notice Testnet-only ERC-20 fixture for custody mechanics. Not USDC, not a
///         stablecoin, no external backing, no economic claim.
contract NomosTestAsset {
    string public constant name = "Nomos Test Asset";
    string public constant symbol = "NTEST";
    uint8 public constant decimals = 18;

    address public owner;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "NTEST_NOT_OWNER");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address next) external onlyOwner {
        require(next != address(0), "NTEST_INVALID_OWNER");
        emit OwnershipTransferred(owner, next);
        owner = next;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "NTEST_INVALID_RECIPIENT");
        require(amount > 0, "NTEST_INVALID_AMOUNT");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(to != address(0), "NTEST_INVALID_RECIPIENT");
        require(balanceOf[msg.sender] >= amount, "NTEST_INSUFFICIENT_BALANCE");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(to != address(0), "NTEST_INVALID_RECIPIENT");
        require(balanceOf[from] >= amount, "NTEST_INSUFFICIENT_BALANCE");
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= amount, "NTEST_INSUFFICIENT_ALLOWANCE");
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - amount;
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}
