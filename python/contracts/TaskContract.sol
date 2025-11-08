// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./RewardContract.sol";
import "./AchievementBadge.sol";

contract TaskContract is Ownable {
    struct TaskStruct {
        uint256 id;
        string description;
        uint256 reward;
        bool completed;
        address worker;
        address creator;
    }
    
    // Mappings
    mapping(uint256 => TaskStruct) public tasks;
    mapping(address => uint256[]) public userTasks;
    mapping(uint256 => address[]) public taskApplicants;
    mapping(uint256 => mapping(address => bool)) public hasApplied;
    
    // State variables
    uint256 public taskCounter;
    address public rewardToken;
    address public achievementBadge;
    
    // Events
    event TaskCreated(uint256 indexed taskId, string description, uint256 reward, address creator);
    event TaskApplied(uint256 indexed taskId, address applicant);
    event TaskAssigned(uint256 indexed taskId, address worker);
    event TaskCompleted(uint256 indexed taskId, address worker, uint256 reward);
    event TaskCancelled(uint256 indexed taskId);
    
    constructor(address _rewardToken, address _achievementBadge) {
        _transferOwnership(msg.sender);
        rewardToken = _rewardToken;
        achievementBadge = _achievementBadge;
        taskCounter = 0;
    }
    
    function createTask(string memory _description, uint256 _reward) public {
        taskCounter++;
        
        tasks[taskCounter] = TaskStruct({
            id: taskCounter,
            description: _description,
            reward: _reward,
            completed: false,
            worker: address(0),
            creator: msg.sender
        });
        
        userTasks[msg.sender].push(taskCounter);
        
        // Update achievement tracking
        if (achievementBadge != address(0)) {
            AchievementBadge badgeContract = AchievementBadge(achievementBadge);
            badgeContract.updateTaskCreation(msg.sender);
        }
        
        emit TaskCreated(taskCounter, _description, _reward, msg.sender);
    }
    
    function applyForTask(uint256 _taskId) public {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        require(!tasks[_taskId].completed, "Task already completed");
        require(tasks[_taskId].worker == address(0), "Task already assigned");
        require(!hasApplied[_taskId][msg.sender], "Already applied for this task");
        
        taskApplicants[_taskId].push(msg.sender);
        hasApplied[_taskId][msg.sender] = true;
        
        emit TaskApplied(_taskId, msg.sender);
    }
    
    function assignTask(uint256 _taskId, address _worker) public {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        require(msg.sender == tasks[_taskId].creator, "Only task creator can assign");
        require(!tasks[_taskId].completed, "Task already completed");
        require(tasks[_taskId].worker == address(0), "Task already assigned");
        require(hasApplied[_taskId][_worker], "Worker must have applied for the task");
        
        tasks[_taskId].worker = _worker;
        
        emit TaskAssigned(_taskId, _worker);
    }
    
    function completeTask(uint256 _taskId) public {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        require(msg.sender == tasks[_taskId].creator, "Only task creator can complete");
        require(!tasks[_taskId].completed, "Task already completed");
        require(tasks[_taskId].worker != address(0), "Task not assigned");
        
        tasks[_taskId].completed = true;
        address worker = tasks[_taskId].worker;
        uint256 reward = tasks[_taskId].reward;
        
        // Mint rewards to the worker
        RewardContract rewardContract = RewardContract(rewardToken);
        rewardContract.mint(worker, reward);
        
        // Update achievement tracking
        if (achievementBadge != address(0)) {
            AchievementBadge badgeContract = AchievementBadge(achievementBadge);
            badgeContract.updateTaskCompletion(worker, reward);
        }
        
        emit TaskCompleted(_taskId, worker, reward);
    }
    
    function cancelTask(uint256 _taskId) public {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        require(msg.sender == tasks[_taskId].creator, "Only task creator can cancel");
        require(!tasks[_taskId].completed, "Task already completed");
        require(tasks[_taskId].worker == address(0), "Task already assigned");
        
        delete tasks[_taskId];
        
        emit TaskCancelled(_taskId);
    }
    
    // View functions
    function getTask(uint256 _taskId) public view returns (TaskStruct memory) {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        return tasks[_taskId];
    }
    
    function getUserTasks(address _user) public view returns (uint256[] memory) {
        return userTasks[_user];
    }
    
    function getTaskApplicants(uint256 _taskId) public view returns (address[] memory) {
        require(_taskId > 0 && _taskId <= taskCounter, "Task does not exist");
        return taskApplicants[_taskId];
    }
    
    function getTasksCount() public view returns (uint256) {
        return taskCounter;
    }
    
    // Admin functions
    function setRewardToken(address _rewardToken) public onlyOwner {
        rewardToken = _rewardToken;
    }
    
    function setAchievementBadge(address _achievementBadge) public onlyOwner {
        achievementBadge = _achievementBadge;
    }
}
