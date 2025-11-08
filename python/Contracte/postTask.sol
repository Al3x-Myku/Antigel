pragma solidity ^0.8.0;

contract TaskManager {
    struct Task {
        uint256 id;
        string description;
        bool completed;
    }

    Task[] private tasks;
    uint256 private nextTaskId;

    event TaskCreated(uint256 id, string description);
    event TaskCompleted(uint256 id);

    function createTask(string memory _description) public {
        tasks.push(Task(nextTaskId, _description, false));
        emit TaskCreated(nextTaskId, _description);
        nextTaskId++;
    }

    function completeTask(uint256 _id) public {
        require(_id < nextTaskId, "Task does not exist");
        Task storage task = tasks[_id];
        require(!task.completed, "Task already completed");
        task.completed = true;
        emit TaskCompleted(_id);
    }

    function getTask(uint256 _id) public view returns (uint256, string memory, bool) {
        require(_id < nextTaskId, "Task does not exist");
        Task storage task = tasks[_id];
        return (task.id, task.description, task.completed);
    }

    function getAllTasks() public view returns (Task[] memory) {
        return tasks;
    }
}
