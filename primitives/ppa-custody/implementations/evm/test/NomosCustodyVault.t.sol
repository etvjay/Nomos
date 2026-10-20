// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {NomosTestAsset} from "../src/NomosTestAsset.sol";
import {NomosCustodyVault} from "../src/NomosCustodyVault.sol";
import {TestBase} from "./TestBase.sol";

contract FailingToken {
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function transfer(address, uint256) external pure returns (bool) {
        return false;
    }

    function transferFrom(address, address, uint256) external pure returns (bool) {
        return false;
    }
}

contract NomosCustodyVaultTest is TestBase {
    NomosTestAsset internal token;
    NomosCustodyVault internal vault;
    address internal authorizer = address(0xA077);
    address internal recipient = address(0xB0B);
    address internal stranger = address(0xBAD);
    uint256 internal constant UNIT = 1e18;

    function setUp() public {
        token = new NomosTestAsset();
        vault = new NomosCustodyVault(authorizer, address(token));
        token.mint(address(this), 10 * UNIT);
        token.approve(address(vault), type(uint256).max);
        vault.deposit(address(token), 5 * UNIT);
    }

    function _authorize(string memory proposalId, uint256 amount, uint256 ttl)
        internal
        returns (bool, string memory)
    {
        vm.prank(authorizer);
        return vault.authorize(
            proposalId,
            address(token),
            recipient,
            amount,
            block.timestamp + ttl
        );
    }

    function testAuthorizeOnlyAuthorizer() public {
        vm.startPrank(stranger);
        vm.expectRevert(bytes("VAULT_CALLER_NOT_AUTHORIZER"));
        vault.authorize("P1", address(token), recipient, UNIT, block.timestamp + 3600);
        vm.stopPrank();
    }

    function testAuthorizeAndSettle() public {
        (bool ok, string memory reason) = _authorize("P1", UNIT, 3600);
        assertTrue(ok);
        assertEq(reason, "");

        NomosCustodyVault.Intent memory authorized = vault.getSettlement("P1");
        assertTrue(authorized.exists);
        assertEq(authorized.status, "AUTHORIZED");
        assertEq(authorized.token, address(token));
        assertEq(authorized.recipient, recipient);
        assertEq(authorized.amount, UNIT);

        vm.prank(stranger);
        (ok, reason) = vault.settle("P1", address(token), recipient, UNIT);
        assertTrue(ok);
        assertEq(reason, "");
        assertEq(token.balanceOf(recipient), UNIT);
        assertEq(token.balanceOf(address(vault)), 4 * UNIT);

        NomosCustodyVault.Intent memory settled = vault.getSettlement("P1");
        assertEq(settled.status, "SETTLED");
        assertEq(settled.settler, stranger);
        assertEq(settled.custodyBefore, 5 * UNIT);
        assertEq(settled.custodyAfter, 4 * UNIT);
        assertEq(settled.recipientBefore, 0);
        assertEq(settled.recipientAfter, UNIT);
        assertEq(settled.attempts, 1);
    }

    function testWrongTokenRefusedNoMutation() public {
        _authorize("P1", UNIT, 3600);
        (bool ok, string memory reason) =
            vault.settle("P1", address(0xDEAD), recipient, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_TOKEN_MISMATCH");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);

        NomosCustodyVault.Intent memory rec = vault.getSettlement("P1");
        assertEq(rec.status, "AUTHORIZED");
        assertEq(rec.reasonCode, "VAULT_TOKEN_MISMATCH");
        assertEq(rec.attempts, 1);
    }

    function testWrongRecipientRefusedNoMutation() public {
        _authorize("P1", UNIT, 3600);
        (bool ok, string memory reason) =
            vault.settle("P1", address(token), stranger, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_RECIPIENT_MISMATCH");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);
    }

    function testWrongAmountRefusedNoMutation() public {
        _authorize("P1", UNIT, 3600);
        (bool ok, string memory reason) =
            vault.settle("P1", address(token), recipient, UNIT + 1);
        assertFalse(ok);
        assertEq(reason, "VAULT_AMOUNT_MISMATCH");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);
    }

    function testReplayRefusedNoMutation() public {
        _authorize("P1", UNIT, 3600);
        vault.settle("P1", address(token), recipient, UNIT);

        (bool ok, string memory reason) =
            vault.settle("P1", address(token), recipient, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_INTENT_ALREADY_SETTLED");
        assertEq(token.balanceOf(address(vault)), 4 * UNIT);
        assertEq(token.balanceOf(recipient), UNIT);
    }

    function testExpiredRefusedNoMutation() public {
        _authorize("P1", UNIT, 10);
        vm.warp(block.timestamp + 11);

        (bool ok, string memory reason) =
            vault.settle("P1", address(token), recipient, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_INTENT_EXPIRED");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);

        NomosCustodyVault.Intent memory rec = vault.getSettlement("P1");
        assertEq(rec.status, "EXPIRED");
        assertEq(rec.reasonCode, "VAULT_INTENT_EXPIRED");
    }

    function testPausedRefusedThenSucceedsAfterUnpause() public {
        _authorize("P1", UNIT, 3600);
        vault.setPaused(true);

        (bool ok, string memory reason) =
            vault.settle("P1", address(token), recipient, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_PAUSED");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);

        vault.setPaused(false);
        (ok, reason) = vault.settle("P1", address(token), recipient, UNIT);
        assertTrue(ok);
        assertEq(token.balanceOf(recipient), UNIT);
    }

    function testPausedAuthorizeRefusedThenRetrySucceeds() public {
        vault.setPaused(true);
        (bool ok, string memory reason) = _authorize("P2", UNIT, 3600);
        assertFalse(ok);
        assertEq(reason, "VAULT_PAUSED");

        NomosCustodyVault.Intent memory refused = vault.getSettlement("P2");
        assertEq(refused.status, "REFUSED");
        assertEq(refused.reasonCode, "VAULT_PAUSED");

        vault.setPaused(false);
        (ok, reason) = _authorize("P2", UNIT, 3600);
        assertTrue(ok);
        (ok, reason) = vault.settle("P2", address(token), recipient, UNIT);
        assertTrue(ok);
        assertEq(token.balanceOf(recipient), UNIT);
    }

    function testInsufficientCustodyThenDepositRecovers() public {
        (bool ok, string memory reason) = _authorize("P1", 6 * UNIT, 3600);
        assertTrue(ok);
        (ok, reason) = vault.settle("P1", address(token), recipient, 6 * UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_INSUFFICIENT_CUSTODY");
        assertEq(token.balanceOf(address(vault)), 5 * UNIT);
        assertEq(token.balanceOf(recipient), 0);

        vault.deposit(address(token), 2 * UNIT);
        (ok, reason) = vault.settle("P1", address(token), recipient, 6 * UNIT);
        assertTrue(ok);
        assertEq(token.balanceOf(recipient), 6 * UNIT);
        assertEq(token.balanceOf(address(vault)), UNIT);
    }

    function testDuplicateAuthorizeRefused() public {
        _authorize("P1", UNIT, 3600);
        (bool ok, string memory reason) = _authorize("P1", UNIT, 3600);
        assertFalse(ok);
        assertEq(reason, "VAULT_INTENT_EXISTS");
    }

    function testSettleUnknownProposal() public {
        (bool ok, string memory reason) =
            vault.settle("NOPE", address(token), recipient, UNIT);
        assertFalse(ok);
        assertEq(reason, "VAULT_INTENT_NOT_FOUND");
    }

    function testTokenNotAllowedOnAuthorize() public {
        vm.prank(authorizer);
        (bool ok, string memory reason) = vault.authorize(
            "P-NA",
            address(0xDEAD),
            recipient,
            UNIT,
            block.timestamp + 3600
        );
        assertFalse(ok);
        assertEq(reason, "VAULT_TOKEN_NOT_ALLOWED");
    }

    function testTransferFailureRecordedNoConsumption() public {
        FailingToken failing = new FailingToken();
        failing.mint(address(vault), 5 * UNIT);
        vault.allowToken(address(failing), true);

        vm.prank(authorizer);
        (bool ok,) = vault.authorize(
            "P-FAIL",
            address(failing),
            recipient,
            UNIT,
            block.timestamp + 3600
        );
        assertTrue(ok);

        (ok, ) = vault.settle("P-FAIL", address(failing), recipient, UNIT);
        assertFalse(ok);
        NomosCustodyVault.Intent memory rec = vault.getSettlement("P-FAIL");
        assertEq(rec.status, "AUTHORIZED");
        assertEq(rec.reasonCode, "VAULT_TRANSFER_FAILED");
        assertEq(failing.balanceOf(recipient), 0);
        assertEq(failing.balanceOf(address(vault)), 5 * UNIT);
    }

    function testOwnerOnlyConfigurationAndWithdraw() public {
        vm.startPrank(stranger);
        vm.expectRevert(bytes("VAULT_NOT_OWNER"));
        vault.setAuthorizer(stranger);
        vm.expectRevert(bytes("VAULT_NOT_OWNER"));
        vault.setPaused(true);
        vm.expectRevert(bytes("VAULT_NOT_OWNER"));
        vault.allowToken(address(token), false);
        vm.expectRevert(bytes("VAULT_NOT_OWNER"));
        vault.withdraw(address(token), stranger, UNIT);
        vm.stopPrank();
    }

    function testEmergencyWithdraw() public {
        vault.withdraw(address(token), recipient, UNIT);
        assertEq(token.balanceOf(recipient), UNIT);
        assertEq(token.balanceOf(address(vault)), 4 * UNIT);
    }
}
