// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @dev Interface for the RewardContract.
 * Only includes the functions the TaskContract needs to call.
 */
interface IRewardContract {
    function mintReward(address to, uint256 id, uint256 amount, bytes memory data) external;
    function mintBatchReward(address to, uint256[] memory ids, uint256[] memory amounts, bytes memory data) external;
}

/**
 * @title TaskContract
 * @dev Manages the creation, progression, and verification of community tasks.
 * This contract is a 'controller' that triggers rewards from the
 * 'RewardContract' (which is the 'vault').
 */
contract TaskContract is ReentrancyGuard {
    
    // Immutable link to the RewardContract
    IRewardContract public immutable rewardContract;

    // Task data structures
    enum TaskStatus { Created, InProgress, Completed, Verified }

    struct Task {
        uint256 id;
        address creator;
        address completer;
        string metadataURI; // Off-chain task details (e.g., in IPFS)
        TaskStatus status;
        uint256[] rewardIds;  // Array of token IDs (e.g., [0, 17])
        uint256[] rewardAmounts; // Array of token amounts (e.g., [100e18, 1])
    }

    uint256 public taskCounter;
    mapping(uint256 => Task) public tasks;

    event TaskCreated(uint256 indexed id, address indexed creator, string metadataURI);
    event TaskClaimed(uint256 indexed id, address indexed completer);
    event TaskCompleted(uint256 indexed id, address indexed completer);
    event TaskVerified(uint256 indexed id, address indexed verifier);

    /**
     * @dev Links this contract to the deployed RewardContract.
     */
    constructor(address _rewardContractAddress) {
        require(_rewardContractAddress != address(0), "Invalid reward contract address");
        rewardContract = IRewardContract(_rewardContractAddress);
    }

    function createTask(
        string calldata _metadataURI,
        uint256[] calldata _rewardIds,
        uint256[] calldata _rewardAmounts
    ) external {
        require(_rewardIds.length == _rewardAmounts.length, "Mismatched rewards");
        require(_rewardIds.length > 0, "No rewards specified");
        
        taskCounter++;
        uint256 newTaskId = taskCounter;

        tasks[newTaskId] = Task({
            id: newTaskId,
            creator: msg.sender,
            completer: address(0),
            metadataURI: _metadataURI,
            status: TaskStatus.Created,
            rewardIds: _rewardIds,
            rewardAmounts: _rewardAmounts
        });

        emit TaskCreated(newTaskId, msg.sender, _metadataURI);
    }

    // --- Other task logic functions (startTask, completeTask) would go here ---
    
    function claimTask(uint256 _taskId) external {
        Task storage task = tasks[_taskId];
        require(task.id != 0, "Task does not exist");
        require(task.status == TaskStatus.Created, "Task not available");
        
        task.status = TaskStatus.InProgress;
        task.completer = msg.sender;
        emit TaskClaimed(_taskId, msg.sender);
    }

    function completeTask(uint256 _taskId) external {
        Task storage task = tasks[_taskId];
        require(task.id != 0, "Task does not exist");
        require(task.completer == msg.sender, "Not authorized to complete");
        require(task.status == TaskStatus.InProgress, "Task not in progress");

        task.status = TaskStatus.Completed;
        emit TaskCompleted(_taskId, msg.sender);
    }


    /**
     * @dev Verifies a completed task and triggers the reward minting.
     * This function is the critical integration point.
     * It MUST be protected against reentrancy.
     */
    function verifyTask(uint256 _taskId) external nonReentrant {
        Task storage task = tasks[_taskId];

        // 1. Check conditions
        require(task.id != 0, "Task does not exist");
        // For this example, only the creator can verify.
        // A real system might have a different verifier role.
        require(msg.sender == task.creator, "Not authorized to verify");
        require(task.status == TaskStatus.Completed, "Task not completed");
        require(task.completer != address(0), "No completer assigned");

        // 2. Update state
        task.status = TaskStatus.Verified;

        // 3. Effect (External Call)
        // This call will ONLY succeed if this contract's address
        // has the MINTER_ROLE on the rewardContract.
        if (task.rewardIds.length == 1) {
            // Use mintReward (singular)
            rewardContract.mintReward(
                task.completer,
                task.rewardIds[0],
                task.rewardAmounts[0],
                "" // Empty data
            );
        } else {
            // Use mintBatchReward (plural)
            rewardContract.mintBatchReward(
                task.completer,
                task.rewardIds,
                task.rewardAmounts,
                "" // Empty data
            );
        }

        emit TaskVerified(_taskId, msg.sender);
    }

    // --- Read Functions ---
    
    function getTask(uint256 _taskId) external view returns (Task memory) {
        return tasks[_taskId];
    }
}
