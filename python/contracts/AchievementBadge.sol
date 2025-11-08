// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title AchievementBadge
 * @dev ERC721 contract for minting achievement NFT badges similar to GitHub badges
 * Users earn badges for completing tasks, reaching milestones, and contributing to the community
 */
contract AchievementBadge is ERC721, ERC721Enumerable, ERC721URIStorage, AccessControl, Ownable {
    using Counters for Counters.Counter;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    
    Counters.Counter private _tokenIdCounter;

    // Achievement Types
    enum AchievementType {
        FIRST_TASK,           // Complete first task
        TASK_MILESTONE_5,     // Complete 5 tasks
        TASK_MILESTONE_10,    // Complete 10 tasks
        TASK_MILESTONE_25,    // Complete 25 tasks
        TASK_MILESTONE_50,    // Complete 50 tasks
        TASK_MILESTONE_100,   // Complete 100 tasks
        EARLY_ADOPTER,        // One of first 100 users
        TOKEN_COLLECTOR_100,  // Earn 100 HLP tokens
        TOKEN_COLLECTOR_500,  // Earn 500 HLP tokens
        TOKEN_COLLECTOR_1000, // Earn 1000 HLP tokens
        COMMUNITY_BUILDER,    // Create 10 tasks
        MENTOR,               // Have 10 tasks completed by others
        STREAK_7,             // Complete tasks 7 days in a row
        STREAK_30,            // Complete tasks 30 days in a row
        TOP_PERFORMER,        // Be in top 10 performers monthly
        HELPFUL_REVIEWER      // Review/verify 50 tasks
    }

    // Badge metadata
    struct Badge {
        AchievementType achievementType;
        string title;
        string description;
        string imageURI;
        uint256 mintedAt;
        uint256 rarity; // 1=Common, 2=Rare, 3=Epic, 4=Legendary
    }

    // Mappings
    mapping(uint256 => Badge) public badges;
    mapping(address => mapping(AchievementType => bool)) public hasAchievement;
    mapping(address => uint256) public tasksCompleted;
    mapping(address => uint256) public tokensEarned;
    mapping(address => uint256) public tasksCreated;
    mapping(address => uint256) public lastTaskCompletionDate;
    mapping(address => uint256) public currentStreak;
    mapping(address => uint256) public maxStreak;

    // Events
    event BadgeMinted(address indexed recipient, uint256 indexed tokenId, AchievementType achievementType);
    event MilestoneReached(address indexed user, AchievementType achievementType);

    constructor(address admin) ERC721("SideQuests Achievement Badge", "SQAB") {
        _transferOwnership(admin);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _tokenIdCounter.increment(); // Start from token ID 1
    }

    /**
     * @dev Mint a badge for a specific achievement
     */
    function mintBadge(
        address recipient,
        AchievementType achievementType,
        string memory tokenURI
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(!hasAchievement[recipient][achievementType], "User already has this achievement");
        
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        _safeMint(recipient, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        // Set badge metadata
        badges[tokenId] = Badge({
            achievementType: achievementType,
            title: getAchievementTitle(achievementType),
            description: getAchievementDescription(achievementType),
            imageURI: tokenURI,
            mintedAt: block.timestamp,
            rarity: getAchievementRarity(achievementType)
        });

        hasAchievement[recipient][achievementType] = true;

        emit BadgeMinted(recipient, tokenId, achievementType);
        emit MilestoneReached(recipient, achievementType);

        return tokenId;
    }

    /**
     * @dev Update user stats and check for new achievements
     */
    function updateTaskCompletion(address user, uint256 tokensReward) external onlyRole(MINTER_ROLE) {
        tasksCompleted[user]++;
        tokensEarned[user] += tokensReward;
        
        // Update streak tracking
        uint256 today = block.timestamp / 86400; // Days since epoch
        uint256 lastDay = lastTaskCompletionDate[user] / 86400;
        
        if (lastDay == 0 || today == lastDay + 1) {
            // Continue or start streak
            currentStreak[user]++;
        } else if (today > lastDay + 1) {
            // Streak broken, reset
            currentStreak[user] = 1;
        }
        // If same day, don't change streak
        
        if (currentStreak[user] > maxStreak[user]) {
            maxStreak[user] = currentStreak[user];
        }
        
        lastTaskCompletionDate[user] = block.timestamp;
        
        // Check for achievements
        _checkTaskAchievements(user);
        _checkTokenAchievements(user);
        _checkStreakAchievements(user);
    }

    /**
     * @dev Update task creation stats
     */
    function updateTaskCreation(address user) external onlyRole(MINTER_ROLE) {
        tasksCreated[user]++;
        _checkCreatorAchievements(user);
    }

    /**
     * @dev Check and mint task completion achievements
     */
    function _checkTaskAchievements(address user) internal {
        uint256 completed = tasksCompleted[user];
        
        if (completed == 1 && !hasAchievement[user][AchievementType.FIRST_TASK]) {
            _mintAchievement(user, AchievementType.FIRST_TASK);
        } else if (completed >= 5 && !hasAchievement[user][AchievementType.TASK_MILESTONE_5]) {
            _mintAchievement(user, AchievementType.TASK_MILESTONE_5);
        } else if (completed >= 10 && !hasAchievement[user][AchievementType.TASK_MILESTONE_10]) {
            _mintAchievement(user, AchievementType.TASK_MILESTONE_10);
        } else if (completed >= 25 && !hasAchievement[user][AchievementType.TASK_MILESTONE_25]) {
            _mintAchievement(user, AchievementType.TASK_MILESTONE_25);
        } else if (completed >= 50 && !hasAchievement[user][AchievementType.TASK_MILESTONE_50]) {
            _mintAchievement(user, AchievementType.TASK_MILESTONE_50);
        } else if (completed >= 100 && !hasAchievement[user][AchievementType.TASK_MILESTONE_100]) {
            _mintAchievement(user, AchievementType.TASK_MILESTONE_100);
        }
    }

    /**
     * @dev Check and mint token collection achievements
     */
    function _checkTokenAchievements(address user) internal {
        uint256 earned = tokensEarned[user];
        
        if (earned >= 100 && !hasAchievement[user][AchievementType.TOKEN_COLLECTOR_100]) {
            _mintAchievement(user, AchievementType.TOKEN_COLLECTOR_100);
        } else if (earned >= 500 && !hasAchievement[user][AchievementType.TOKEN_COLLECTOR_500]) {
            _mintAchievement(user, AchievementType.TOKEN_COLLECTOR_500);
        } else if (earned >= 1000 && !hasAchievement[user][AchievementType.TOKEN_COLLECTOR_1000]) {
            _mintAchievement(user, AchievementType.TOKEN_COLLECTOR_1000);
        }
    }

    /**
     * @dev Check and mint streak achievements
     */
    function _checkStreakAchievements(address user) internal {
        uint256 streak = currentStreak[user];
        
        if (streak >= 7 && !hasAchievement[user][AchievementType.STREAK_7]) {
            _mintAchievement(user, AchievementType.STREAK_7);
        } else if (streak >= 30 && !hasAchievement[user][AchievementType.STREAK_30]) {
            _mintAchievement(user, AchievementType.STREAK_30);
        }
    }

    /**
     * @dev Check and mint creator achievements
     */
    function _checkCreatorAchievements(address user) internal {
        uint256 created = tasksCreated[user];
        
        if (created >= 10 && !hasAchievement[user][AchievementType.COMMUNITY_BUILDER]) {
            _mintAchievement(user, AchievementType.COMMUNITY_BUILDER);
        }
    }

    /**
     * @dev Internal function to mint achievements with default URI
     */
    function _mintAchievement(address user, AchievementType achievementType) internal {
        string memory tokenURI = getDefaultTokenURI(achievementType);
        
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        _safeMint(user, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        badges[tokenId] = Badge({
            achievementType: achievementType,
            title: getAchievementTitle(achievementType),
            description: getAchievementDescription(achievementType),
            imageURI: tokenURI,
            mintedAt: block.timestamp,
            rarity: getAchievementRarity(achievementType)
        });

        hasAchievement[user][achievementType] = true;

        emit BadgeMinted(user, tokenId, achievementType);
        emit MilestoneReached(user, achievementType);
    }

    /**
     * @dev Get achievement title
     */
    function getAchievementTitle(AchievementType achievementType) public pure returns (string memory) {
        if (achievementType == AchievementType.FIRST_TASK) return "First Quest";
        if (achievementType == AchievementType.TASK_MILESTONE_5) return "Getting Started";
        if (achievementType == AchievementType.TASK_MILESTONE_10) return "Task Hunter";
        if (achievementType == AchievementType.TASK_MILESTONE_25) return "Dedicated Worker";
        if (achievementType == AchievementType.TASK_MILESTONE_50) return "Veteran Quester";
        if (achievementType == AchievementType.TASK_MILESTONE_100) return "Quest Master";
        if (achievementType == AchievementType.EARLY_ADOPTER) return "Early Adopter";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_100) return "Token Collector";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_500) return "Wealth Builder";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_1000) return "Token Whale";
        if (achievementType == AchievementType.COMMUNITY_BUILDER) return "Community Builder";
        if (achievementType == AchievementType.MENTOR) return "Mentor";
        if (achievementType == AchievementType.STREAK_7) return "Week Warrior";
        if (achievementType == AchievementType.STREAK_30) return "Monthly Champion";
        if (achievementType == AchievementType.TOP_PERFORMER) return "Top Performer";
        if (achievementType == AchievementType.HELPFUL_REVIEWER) return "Helpful Reviewer";
        return "Unknown Achievement";
    }

    /**
     * @dev Get achievement description
     */
    function getAchievementDescription(AchievementType achievementType) public pure returns (string memory) {
        if (achievementType == AchievementType.FIRST_TASK) return "Completed your first task on SideQuests";
        if (achievementType == AchievementType.TASK_MILESTONE_5) return "Completed 5 tasks";
        if (achievementType == AchievementType.TASK_MILESTONE_10) return "Completed 10 tasks";
        if (achievementType == AchievementType.TASK_MILESTONE_25) return "Completed 25 tasks";
        if (achievementType == AchievementType.TASK_MILESTONE_50) return "Completed 50 tasks";
        if (achievementType == AchievementType.TASK_MILESTONE_100) return "Completed 100 tasks";
        if (achievementType == AchievementType.EARLY_ADOPTER) return "One of the first 100 users";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_100) return "Earned 100 HLP tokens";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_500) return "Earned 500 HLP tokens";
        if (achievementType == AchievementType.TOKEN_COLLECTOR_1000) return "Earned 1000 HLP tokens";
        if (achievementType == AchievementType.COMMUNITY_BUILDER) return "Created 10 tasks";
        if (achievementType == AchievementType.MENTOR) return "Had 10 tasks completed by others";
        if (achievementType == AchievementType.STREAK_7) return "Completed tasks 7 days in a row";
        if (achievementType == AchievementType.STREAK_30) return "Completed tasks 30 days in a row";
        if (achievementType == AchievementType.TOP_PERFORMER) return "Top 10 performer of the month";
        if (achievementType == AchievementType.HELPFUL_REVIEWER) return "Reviewed/verified 50 tasks";
        return "Unknown Achievement";
    }

    /**
     * @dev Get achievement rarity
     */
    function getAchievementRarity(AchievementType achievementType) public pure returns (uint256) {
        if (achievementType == AchievementType.FIRST_TASK) return 1; // Common
        if (achievementType == AchievementType.TASK_MILESTONE_5) return 1; // Common
        if (achievementType == AchievementType.TASK_MILESTONE_10) return 2; // Rare
        if (achievementType == AchievementType.TASK_MILESTONE_25) return 2; // Rare
        if (achievementType == AchievementType.TASK_MILESTONE_50) return 3; // Epic
        if (achievementType == AchievementType.TASK_MILESTONE_100) return 4; // Legendary
        if (achievementType == AchievementType.EARLY_ADOPTER) return 3; // Epic
        if (achievementType == AchievementType.TOKEN_COLLECTOR_100) return 1; // Common
        if (achievementType == AchievementType.TOKEN_COLLECTOR_500) return 2; // Rare
        if (achievementType == AchievementType.TOKEN_COLLECTOR_1000) return 3; // Epic
        if (achievementType == AchievementType.COMMUNITY_BUILDER) return 2; // Rare
        if (achievementType == AchievementType.MENTOR) return 3; // Epic
        if (achievementType == AchievementType.STREAK_7) return 2; // Rare
        if (achievementType == AchievementType.STREAK_30) return 4; // Legendary
        if (achievementType == AchievementType.TOP_PERFORMER) return 4; // Legendary
        if (achievementType == AchievementType.HELPFUL_REVIEWER) return 3; // Epic
        return 1; // Common by default
    }

    /**
     * @dev Get default token URI for achievement type
     */
    function getDefaultTokenURI(AchievementType achievementType) public pure returns (string memory) {
        // In a real implementation, these would point to actual metadata JSON files
        string memory baseURI = "https://api.sidequests.com/badges/";
        
        if (achievementType == AchievementType.FIRST_TASK) return string(abi.encodePacked(baseURI, "first-task.json"));
        if (achievementType == AchievementType.TASK_MILESTONE_5) return string(abi.encodePacked(baseURI, "milestone-5.json"));
        if (achievementType == AchievementType.TASK_MILESTONE_10) return string(abi.encodePacked(baseURI, "milestone-10.json"));
        if (achievementType == AchievementType.TASK_MILESTONE_25) return string(abi.encodePacked(baseURI, "milestone-25.json"));
        if (achievementType == AchievementType.TASK_MILESTONE_50) return string(abi.encodePacked(baseURI, "milestone-50.json"));
        if (achievementType == AchievementType.TASK_MILESTONE_100) return string(abi.encodePacked(baseURI, "milestone-100.json"));
        if (achievementType == AchievementType.EARLY_ADOPTER) return string(abi.encodePacked(baseURI, "early-adopter.json"));
        if (achievementType == AchievementType.TOKEN_COLLECTOR_100) return string(abi.encodePacked(baseURI, "tokens-100.json"));
        if (achievementType == AchievementType.TOKEN_COLLECTOR_500) return string(abi.encodePacked(baseURI, "tokens-500.json"));
        if (achievementType == AchievementType.TOKEN_COLLECTOR_1000) return string(abi.encodePacked(baseURI, "tokens-1000.json"));
        if (achievementType == AchievementType.COMMUNITY_BUILDER) return string(abi.encodePacked(baseURI, "community-builder.json"));
        if (achievementType == AchievementType.MENTOR) return string(abi.encodePacked(baseURI, "mentor.json"));
        if (achievementType == AchievementType.STREAK_7) return string(abi.encodePacked(baseURI, "streak-7.json"));
        if (achievementType == AchievementType.STREAK_30) return string(abi.encodePacked(baseURI, "streak-30.json"));
        if (achievementType == AchievementType.TOP_PERFORMER) return string(abi.encodePacked(baseURI, "top-performer.json"));
        if (achievementType == AchievementType.HELPFUL_REVIEWER) return string(abi.encodePacked(baseURI, "helpful-reviewer.json"));
        
        return string(abi.encodePacked(baseURI, "default.json"));
    }

    /**
     * @dev Get user's badges
     */
    function getUserBadges(address user) external view returns (uint256[] memory) {
        uint256 balance = balanceOf(user);
        uint256[] memory tokenIds = new uint256[](balance);
        
        for (uint256 i = 0; i < balance; i++) {
            tokenIds[i] = tokenOfOwnerByIndex(user, i);
        }
        
        return tokenIds;
    }

    /**
     * @dev Get user stats
     */
    function getUserStats(address user) external view returns (
        uint256 _tasksCompleted,
        uint256 _tokensEarned,
        uint256 _tasksCreated,
        uint256 _currentStreak,
        uint256 _maxStreak
    ) {
        return (
            tasksCompleted[user],
            tokensEarned[user],
            tasksCreated[user],
            currentStreak[user],
            maxStreak[user]
        );
    }

    /**
     * @dev Grant minter role
     */
    function grantMinterRole(address account) public onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(MINTER_ROLE, account);
    }

    /**
     * @dev Revoke minter role
     */
    function revokeMinterRole(address account) public onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(MINTER_ROLE, account);
    }

    // Required overrides for multiple inheritance
    function _beforeTokenTransfer(address from, address to, uint256 tokenId, uint256 batchSize)
        internal
        override(ERC721, ERC721Enumerable)
    {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }

    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}