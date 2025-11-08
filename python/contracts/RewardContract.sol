// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title RewardContract
 * @dev Manages all community rewards (fungible and non-fungible)
 * using the ERC-1155 standard.
 * - ID 0: CommunityToke (Fungible)
 * - ID 1...N: Unique NFT Badges (Non-Fungible)
 *
 * Access is controlled by AccessControl:
 * - DEFAULT_ADMIN_ROLE: The deployer/DAO, can grant roles.
 * - MINTER_ROLE: The TaskContract, can mint new tokens/badges.
 * - PAUSER_ROLE: The deployer/DAO, can pause the contract.
 */
contract RewardContract is ERC1155, AccessControl, Pausable {
    // Role definitions
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    // Token ID for the fungible community token
    uint256 public constant COMMUNITY_TOKE_ID = 0;

    constructor(address admin) ERC1155("https://api.mycommunity.app/meta/{id}.json") {
        // Grant the deployer (or a multisig) the admin and pauser roles
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
    }

    /**
     * @dev Mints rewards.
     * Restricted to accounts with MINTER_ROLE (i.e., the TaskContract).
     */
    function mintReward(
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) public virtual onlyRole(MINTER_ROLE) whenNotPaused {
        _mint(to, id, amount, data);
    }

    /**
     * @dev Mints a batch of rewards.
     * Restricted to accounts with MINTER_ROLE (i.e., the TaskContract).
     */
    function mintBatchReward(
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) public virtual onlyRole(MINTER_ROLE) whenNotPaused {
        _mintBatch(to, ids, amounts, data);
    }

    // --- Admin Functions ---

    function pause() public virtual onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() public virtual onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // --- Overrides ---

    /**
     * @dev See {ERC1155-_update}.
     * Added 'whenNotPaused' hook to all token transfers.
     */
    function _beforeTokenTransfer(
        address operator,
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) internal virtual override(ERC1155) {
        super._beforeTokenTransfer(operator, from, to, ids, amounts, data);
        require(!paused(), "ERC1155: token transfer while paused");
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(ERC1155, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
