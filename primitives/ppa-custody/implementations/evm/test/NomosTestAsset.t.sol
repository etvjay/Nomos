// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {NomosTestAsset} from "../src/NomosTestAsset.sol";
import {TestBase} from "./TestBase.sol";

contract NomosTestAssetTest is TestBase {
    NomosTestAsset internal token;
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    function setUp() public {
        token = new NomosTestAsset();
    }

    function testMetadata() public view {
        assertEq(token.name(), "Nomos Test Asset");
        assertEq(token.symbol(), "NTEST");
        assertEq(uint256(token.decimals()), 18);
        assertEq(token.owner(), address(this));
        assertEq(token.totalSupply(), 0);
    }

    function testMintOnlyOwner() public {
        token.mint(alice, 100);
        assertEq(token.balanceOf(alice), 100);
        assertEq(token.totalSupply(), 100);

        vm.startPrank(alice);
        vm.expectRevert(bytes("NTEST_NOT_OWNER"));
        token.mint(alice, 1);
        vm.stopPrank();
    }

    function testMintRejectsZero() public {
        vm.expectRevert(bytes("NTEST_INVALID_RECIPIENT"));
        token.mint(address(0), 1);

        vm.expectRevert(bytes("NTEST_INVALID_AMOUNT"));
        token.mint(alice, 0);
    }

    function testTransfer() public {
        token.mint(address(this), 100);
        token.transfer(alice, 40);
        assertEq(token.balanceOf(address(this)), 60);
        assertEq(token.balanceOf(alice), 40);

        vm.startPrank(alice);
        vm.expectRevert(bytes("NTEST_INSUFFICIENT_BALANCE"));
        token.transfer(bob, 41);
        vm.stopPrank();
    }

    function testApproveAndTransferFrom() public {
        token.mint(alice, 100);
        vm.prank(alice);
        token.approve(address(this), 30);

        token.transferFrom(alice, bob, 30);
        assertEq(token.balanceOf(alice), 70);
        assertEq(token.balanceOf(bob), 30);
        assertEq(token.allowance(alice, address(this)), 0);

        vm.expectRevert(bytes("NTEST_INSUFFICIENT_ALLOWANCE"));
        token.transferFrom(alice, bob, 1);
    }
}
