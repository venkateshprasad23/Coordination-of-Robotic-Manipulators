# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC San Diego.
# Created by Yuzhe Qin, Fanbo Xiang

from final_env import FinalEnv, SolutionBase
import numpy as np
from sapien.core import Pose
from transforms3d.euler import euler2quat, quat2euler
from transforms3d.quaternions import quat2axangle, qmult, qinverse


class Solution(SolutionBase):
    """
    This is a very bad baseline solution
    It operates in the following ways:
    1. roughly align the 2 spades
    2. move the spades towards the center
    3. lift 1 spade and move the other away
    4. somehow transport the lifted spade to the bin
    5. pour into the bin
    6. go back to 1
    """

    def init(self, env: FinalEnv):
        self.phase = 0
        self.counter = 0
        self.drive = 0
        meta = env.get_metadata()
        self.box_ids = meta['box_ids']
        self.timestep = meta['timestep']
        self.bin_id = meta['bin_id']
        r1, r2, c1, c2, c3, c4 = env.get_agents()

        self.ps = [1000, 800, 600, 600, 200, 200, 100]
        self.ds = [1000, 800, 600, 600, 200, 200, 100]
        r1.configure_controllers(self.ps, self.ds)
        r2.configure_controllers(self.ps, self.ds)

    def act(self, env: FinalEnv, current_timestep: int):
        r1, r2, c1, c2, c3, c4 = env.get_agents()

        pf_left = r1.get_compute_functions()['passive_force'](True, True, False)
        pf_right = r2.get_compute_functions()['passive_force'](True, True, False)

        if self.phase == 0:
            self.counter += 1
            t1 = [2, 1, 0, -1.5, -1, 1, -2]
            t2 = [-2, 1, 0, -1.5, 1, 1, -2]

            r1.set_action(t1, [0] * 7, pf_left)
            r2.set_action(t2, [0] * 7, pf_right)

            if self.counter > 2000:
                return False

            if np.allclose(r1.get_observation()[0], t1, 0.05, 0.05) and np.allclose(
                    r2.get_observation()[0], t2, 0.05, 0.05):
                self.phase = 1
                self.counter = 0
                self.selected_x = None
                print("Phase 1")

        if self.phase == 1:
            self.counter += 1

            if self.counter == 1:
                selected = self.pick_box(c1)
                if selected is False:
                    return False
                else:
                    self.selected_x = selected[0]
                    self.selected_y = selected[1]
                    self.selected_z = selected[2]

                    print("First time choosing", self.selected_x)
                    if self.selected_x < -0.3 or self.selected_x > 0.16 or self.selected_y < -0.28 or self.selected_y > 0.28 or self.selected_z > 0.7:
                        for i in range(10):
                            selected = self.pick_box(c1)
                            self.selected_x = selected[0]
                            self.selected_y = selected[1]
                            self.selected_z = selected[2]
                            if -0.3 < self.selected_x < 0.16 and -0.28 < self.selected_y < 0.28 and self.selected_z < 0.7:
                                print(i, "th time choosing", self.selected_x)
                                break

            target_pose_left = Pose([self.selected_x - 0.02, 0.5, 0.676], euler2quat(np.pi, -np.pi / 3, -np.pi / 2))
            target_pose_right = Pose([self.selected_x - 0.04, -0.5, 0.6], euler2quat(np.pi, -np.pi / 3, np.pi / 2))
            self.move_to_target_pose_with_internal_controller(r1, 9, target_pose_left, self.counter, 2000 / 5 + 1)
            self.move_to_target_pose_with_internal_controller(r2, 9, target_pose_right, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r1, 9, target_pose_left, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r2, 9, target_pose_right, self.counter, 2000 / 5 + 1)
            # self.diff_drive(r1, 9, target_pose_left)
            # self.diff_drive(r2, 9, target_pose_right)
            if self.counter == (2000 / 5):
                self.phase = 2
                self.counter = 0
                print("Phase 2")

                pose = r1.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[1] = 0.065
                self.pose_left = Pose(p, q)

                pose = r2.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[1] = -0.065
                self.pose_right = Pose(p, q)

        if self.phase == 2:
            self.counter += 1
            self.move_to_target_pose_with_internal_controller(r1, 9, self.pose_left, self.counter, 2000 / 5 + 1)
            self.move_to_target_pose_with_internal_controller(r2, 9, self.pose_right, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r2, 9, self.pose_right, self.counter, 2000 / 5 + 1)
            # self.diff_drive(r1, 9, self.pose_left)
            # self.diff_drive(r2, 9, self.pose_right)

            if self.counter == (2000 / 5):
                self.phase = 3
                self.counter = 0
                print("Phase 3")

                pose = r2.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[2] += 0.15
                p[1] = 0.05
                p[0] -= 0.05
                q = euler2quat(np.pi, -np.pi / 1.5, np.pi / 2)
                self.pose_right = Pose(p, q)

                pose = r1.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[0] += 0.05
                p[1] -= 0.05
                p[2] = 1.2
                q = euler2quat(np.pi, -np.pi / 5, -np.pi / 2)
                self.pose_left = Pose(p, q)

        if self.phase == 3:
            self.counter += 1
            self.move_to_target_pose_with_internal_controller(r1, 9, self.pose_left, self.counter, 2000 / 5 + 1)
            self.move_to_target_pose_with_internal_controller(r2, 9, self.pose_right, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left, self.counter, 2000 / 5 + 1)
            # self.move_to_target_pose_with_user_controller(r2, 9, self.pose_right, self.counter, 2000 / 5 + 1)
            # self.diff_drive(r1, 9, self.pose_left)
            # self.diff_drive(r2, 9, self.pose_right)

            if self.counter == (2000 / 5):
                self.phase = 4
                self.counter = 0
                print("First Part of phase 4")

                count = self.n_box_spade(c4)
                count1 = self.n_box_spade(c1)
                c = max(count1, count)
                print("Box on spades", c)
                if c == 0:
                    self.phase = 0
                    self.counter = 0

                pose = r1.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[1] = 0.5
                q = euler2quat(np.pi, -np.pi / 3, -np.pi / 2)
                self.pose_left = Pose(p, q)

        if self.phase == 4:
            self.counter += 1
            if self.counter < 3000 / 10:
                # self.move_to_target_pose_with_internal_controller(r1, 9, self.pose_left, self.counter, 3000 / 10 + 1)
                # self.move_to_target_pose_with_internal_controller(r2, 9, r2.get_observation()[2][9], self.counter,
                #                                                   3000 / 10 + 1, [0, 1, 2, 3], [-2, 0.3, 0.3, -3])
                self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left, self.counter, 3000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r2, 9, r2.get_observation()[2][9], self.counter,
                                                                  3000 / 10 + 1, [0, 1, 2, 3], [-2, 0.3, 0.3, -3])
                # self.diff_drive(r1, 9, self.pose_left)
                # self.diff_drive(r2, 9, r2.get_observation()[2][9], [0, 1, 2, 3], [-2, 0.3, 0.3, -3])
            elif self.counter < 6000 / 10:
                # self.move_to_target_pose_with_internal_controller(r1, 9, self.left,
                #                                                   self.counter - 3000 / 10,
                #                                                   6000 / 10 + 1, [0, 1, 2, 3], [1, 0.3, 0.3, -3])
                # self.move_to_target_pose_with_internal_controller(r2, 9, r2.get_observation()[2][9],
                #                                                   self.counter - 3000 / 10,
                #                                                   6000 / 10 + 1, [0, 1, 2, 3], [1, 0.3, 0.3, -3])
                self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left,
                                                              self.counter - 3000 / 10,
                                                              6000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r2, 9, r2.get_observation()[2][9],
                                                                  self.counter - 3000 / 10,
                                                                  6000 / 10 + 1, [0, 1, 2, 3], [1, 0.3, 0.3, -3])
                # self.diff_drive(r1, 9, self.pose_left)
                # self.diff_drive(r2, 9, r2.get_observation()[2][9], [0, 1, 2, 3], [1, 0.3, 0.3, -3])
            elif self.counter == 6000 / 10:
                print("Second Part of phase 4")

                pose = r2.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[2] = 1.25
                self.pose_right = Pose(p, q)
            elif self.counter < 9000 / 10:
                # self.move_to_target_pose_with_internal_controller(r1, 9, self.pose_left,
                #                                                   self.counter - 6000 / 10,
                #                                                   9000 / 10 + 1)
                # self.move_to_target_pose_with_internal_controller(r2, 9, self.pose_right,
                #                                                   self.counter - 6000 / 10,
                #                                                   9000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left,
                                                              self.counter - 6000 / 10,
                                                              9000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r2, 9, self.pose_right,
                                                                  self.counter - 6000 / 10,
                                                                  9000 / 10 + 1)
                # self.diff_drive(r1, 9, self.pose_left)
                # self.diff_drive(r2, 9, self.pose_right)
            elif self.counter == 9000 / 10:
                pose = r2.get_observation()[2][9]
                p, q = pose.p, pose.q
                p[:2] = self.bin_pos(c4)[:2] + np.array([0.01, 0.05])
                self.pose_right = Pose(p, q)
            elif self.counter < 12000 / 10:
                # self.move_to_target_pose_with_internal_controller(r1, 9, self.pose_left, self.counter - 9000 / 10,
                #                                                   12000 / 10 + 1)
                # self.move_to_target_pose_with_internal_controller(r2, 9, self.pose_right, self.counter - 9000 / 10,
                #                                                   12000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left, self.counter - 9000 / 10,
                                                              12000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r2, 9, self.pose_right, self.counter - 9000 / 10,
                                                                  12000 / 10 + 1)
                # self.diff_drive(r1, 9, self.pose_left)
                # self.diff_drive(r2, 9, self.pose_right)
            elif self.counter < 15000 / 10:
                # self.move_to_target_pose_with_internal_controller(r2, 9, r2.get_observation()[2][9],
                #                                                   self.counter - 12000 / 10,
                #                                                   15000 / 10 + 1, [6], [4])
                self.move_to_target_pose_with_user_controller(r1, 9, self.pose_left,
                                                              self.counter - 12000 / 10,
                                                              15000 / 10 + 1)
                self.move_to_target_pose_with_user_controller(r2, 9, r2.get_observation()[2][9],
                                                                  self.counter - 12000 / 10,
                                                                  15000 / 10 + 1, [6], [4])
                # self.diff_drive(r1, 9, self.pose_left)
                # self.diff_drive(r2, 9, r2.get_observation()[2][9], [6], [4])
            else:
                self.phase = 0
                self.counter = 0

    @staticmethod
    def pose2mat(pose: Pose) -> np.ndarray:
        """You need to implement this function

        You will need to implement this function first before any other functions.
        In this function, you need to convert a (position: pose.p, quaternion: pose.q) into a SE(3) matrix

        You can not directly use external library to transform quaternion into rotation matrix.
        Only numpy can be used here.
        Args:
            pose: sapien Pose object, where Pose.p and Pose.q are position and quaternion respectively

        Hint: the convention of quaternion

        Returns:
            (4, 4) transformation matrix represent the same pose

        """
        mat44 = np.eye(4)
        mat44[:3, 3] = pose.p

        quat = np.array(pose.q).reshape([4, 1])
        if np.linalg.norm(quat) < np.finfo(np.float).eps:
            return mat44
        quat /= np.linalg.norm(quat, axis=0, keepdims=False)
        img = quat[1:, :]
        w = quat[0, 0]

        Eq = np.concatenate([-img, w * np.eye(3) + skew(img)], axis=1)  # (3, 4)
        Gq = np.concatenate([-img, w * np.eye(3) - skew(img)], axis=1)  # (3, 4)
        mat44[:3, :3] = Eq @ Gq.T
        return mat44

    def pose2exp_coordinate(self, pose: np.ndarray):
        """You may need to implement this function

        Compute the exponential coordinate corresponding to the given SE(3) matrix
        Note: unit twist is not a unit vector

        Args:
            pose: (4, 4) transformation matrix

        Returns:
            Unit twist: (6, ) vector represent the unit twist
            Theta: scalar represent the quantity of exponential coordinate
        """

        def rot2so3(rotation: np.ndarray):
            assert rotation.shape == (3, 3)
            if np.isclose(rotation.trace(), 3):
                return np.zeros(3), 1
            if np.isclose(rotation.trace(), -1):
                raise RuntimeError
            theta = np.arccos((rotation.trace() - 1) / 2)
            omega = 1 / 2 / np.sin(theta) * np.array(
                [rotation[2, 1] - rotation[1, 2], rotation[0, 2] - rotation[2, 0], rotation[1, 0] - rotation[0, 1]]).T
            return omega, theta

        omega, theta = rot2so3(pose[:3, :3])
        ss = skew(omega)
        inv_left_jacobian = np.eye(3, dtype=np.float) / theta - 0.5 * ss + (
                1.0 / theta - 0.5 / np.tan(theta / 2)) * ss @ ss
        v = inv_left_jacobian @ pose[:3, 3]
        return np.concatenate([omega, v]), theta

    def compute_joint_velocity_from_twist(self, robot, index, twist: np.ndarray) -> np.ndarray:
        """You need to implement this function

        This function is a kinematic-level calculation which do not consider dynamics.
        Pay attention to the frame of twist, is it spatial twist or body twist

        Jacobian is provided for your, so no need to compute the velocity kinematics
        ee_jacobian is the geometric Jacobian on account of only the joint of robot arm, not gripper
        Jacobian in SAPIEN is defined as the derivative of spatial twist with respect to joint velocity

        Args:
            twist: (6,) vector to represent the twist

        Returns:
            (7, ) vector for the velocity of arm joints (not include gripper)

        """
        assert twist.size == 6
        # Jacobian define in SAPIEN use twist (v, \omega) which is different from the definition in the slides
        # So we perform the matrix block operation below
        # dense_jacobian = self.robot.compute_spatial_twist_jacobian()  # (num_link * 6, dof())
        dense_jacobian = robot.get_compute_functions()['spatial_twist_jacobian']()  # (num_link * 6, dof())
        ee_jacobian = np.zeros([6, robot.dof])  # (6, 7)
        ee_jacobian[:3, :] = dense_jacobian[index * 6 - 3:index * 6, :7]
        ee_jacobian[3:6, :] = dense_jacobian[(index - 1) * 6:index * 6 - 3, :7]

        inverse_jacobian = np.linalg.pinv(ee_jacobian)
        return inverse_jacobian @ twist

    def move_to_target_pose_with_internal_controller(self, robot, index, target_pose: Pose, counter, num_steps,
                                                     js2=None, joint_target=None) -> None:
        """You need to implement this function

        Move the robot hand dynamically to a given target pose
        You may need to call self.internal_controller and your self.compute_joint_velocity_from_twist in this function

        To make command (e.g. internal controller) take effect and simulate all the physical effects, you need to step
        the simulation world for one step and render the new scene for visualization by something like:
            for i in range(num_step):
                # Do something
                self.internal_controller(target_joint_velocity)
                self.step()
                self.render()

        Args:
            target_ee_pose: Pose #(4, 4) transformation of robot hand in robot base frame (ee2base)
            num_steps: how much steps to reach to target pose, each step correspond to self.scene.get_timestep() seconds
                in physical simulation

        """
        executed_time = num_steps * self.timestep
        target_ee_pose = self.pose2mat(target_pose)

        def calculate_twist(time_to_target):
            # relative_transform = self.pose2mat(self.end_effector.get_pose().inv()) @ target_ee_pose
            relative_transform = self.pose2mat(robot.get_observation()[2][9].inv()) @ target_ee_pose
            unit_twist, theta = self.pose2exp_coordinate(relative_transform)
            velocity = theta / time_to_target
            body_twist = unit_twist * velocity
            return adjoint_matrix(self.pose2mat(robot.get_observation()[2][9])) @ body_twist

        spatial_twist = calculate_twist(executed_time)

        if counter % 100 == 0:
            spatial_twist = calculate_twist((num_steps - counter) * self.timestep)
        pf = robot.get_compute_functions()['passive_force'](True, True, False)
        qpos, qvel, poses = robot.get_observation()
        qvel = self.compute_joint_velocity_from_twist(robot, index, spatial_twist)
        if js2 is not None:
            for j, target in zip(js2, joint_target):
                qpos[j] = target
        robot.set_action(qpos, qvel, pf)
        return

    def move_to_target_pose_with_user_controller(self, robot, index, target_pose: Pose, counter, num_steps,
                                                 js2=None, joint_target=None) -> None:
        """You need to implement this function

        Similar to self.move_to_target_pose_with_internal_controller. However, this time you need to implement your own
        controller instead of the SAPIEN internal controller.

        You can use anything you want to perform dynamically execution of the robot, e.g. PID, compute torque control
        You can write additional class or function to help implement this function.
        You can also use the inverse kinematics to calculate target joint position.
        You do not need to follow the given timestep exactly if you do not know how to do that.

        However, you are not allow to magically set robot's joint position and velocity using set_qpos() and set_qvel()
        in this function. You need to control the robot by applying appropriate force on the robot like real-world.

        There are two function you may need to use (optional):
            gravity_compensation = self.robot.compute_passive_force(gravity=False, coriolis_and_centrifugal=True,
                                                                    external=False)
            coriolis_and_centrifugal_compensation = self.robot.compute_passive_force(gravity=False,
                                                                                    coriolis_and_centrifugal=True,
                                                                                    external=False)

        The first function calculate how much torque each joint need to apply in order to balance the gravity
        Similarly, the second function calculate how much torque to balance the coriolis and centrifugal force

        To controller your robot actuator dynamically (actuator is mounted on each joint), you can use
        self.robot.set_qf(joint_torque)
        Note that joint_torque is a (9, ) vector which also includes the joint torque of two gripper

        Args:
            target_ee_pose: (4, 4) transformation of robot hand in robot base frame (ee2base)
            num_steps: how much steps to reach to target pose, each step correspond to self.scene.get_timestep() seconds

        """
        timestep = self.timestep
        target_ee_pose = self.pose2mat(target_pose)

        def calculate_twist(time_to_target):
            relative_transform = self.pose2mat(robot.get_observation()[2][9].inv()) @ target_ee_pose
            unit_twist, theta = self.pose2exp_coordinate(relative_transform)
            velocity = theta / time_to_target
            body_twist = unit_twist * velocity
            return adjoint_matrix(self.pose2mat(robot.get_observation()[2][9])) @ body_twist

        pids = []
        pid_parameters = [(1000, 1000, 0), (800, 800, 0), (600, 600, 0),
                          (600, 600, 0), (200, 200, 0), (200, 200, 0), (100, 100, 0)]
        # pid_parameters = [(400, 400, 10), (400, 400, 10), (400, 400, 5), (300, 200, 4), (200, 200., 4), (200, 200., 3),
        #                   (200, 200., 3)]
        PID = SimplePID()

        for i in range(7):
            pids.append(SimplePID(pid_parameters[i][0], pid_parameters[i][1], pid_parameters[i][2]))

        target_qpos = robot.get_observation()[0]

        # for i in range(num_steps):
        spatial_twist = calculate_twist((num_steps - counter) * timestep)

        target_joint_velocity = self.compute_joint_velocity_from_twist(robot, index, spatial_twist)
        target_qpos += target_joint_velocity * timestep
        qf = robot.get_compute_functions()['passive_force'](True, True, False)
        pid_qf = PID.pid_forward(pids, target_qpos, robot.get_observation()[0], timestep)
        qf += pid_qf

        # self.robot.set_qf(qf)
        if js2 is not None:
            for j, target in zip(js2, joint_target):
                target_qpos[j] = target
        robot.set_action(target_qpos, target_joint_velocity, qf)

    def diff_drive(self, robot, index, target_pose, js2 = None, joint_target = None):
        """
        this diff drive is very hacky
        it tries to transport the target pose to match an end pose
        by computing the pose difference between current pose and target pose
        then it estimates a cartesian velocity for the end effector to follow.
        It uses differential IK to compute the required joint velocity, and set
        the joint velocity as current step target velocity.
        This technique makes the trajectory very unstable but it still works some times.
        """
        pf = robot.get_compute_functions()['passive_force'](True, True, False)
        max_v = 0.1
        max_w = np.pi
        qpos, qvel, poses = robot.get_observation()
        current_pose: Pose = poses[index]
        delta_p = target_pose.p - current_pose.p
        delta_q = qmult(target_pose.q, qinverse(current_pose.q))

        axis, theta = quat2axangle(delta_q)
        if (theta > np.pi):
            theta -= np.pi * 2

        t1 = np.linalg.norm(delta_p) / max_v
        t2 = theta / max_w
        t = max(np.abs(t1), np.abs(t2), 0.001)
        thres = 0.1
        if t < thres:
            k = (np.exp(thres) - 1) / thres
            t = np.log(k * t + 1)
        v = delta_p / t
        w = theta / t * axis
        target_qvel = robot.get_compute_functions()['cartesian_diff_ik'](np.concatenate((v, w)), 9)
        if js2 is not None:
            for j, target in zip(js2, joint_target):
                qpos[j] = target
        robot.set_action(qpos, target_qvel, pf)

    def get_global_position_from_camera(self, camera, depth, x, y):
        """
        camera: an camera agent
        depth: the depth obsrevation
        x, y: the horizontal, vertical index for a pixel, you would access the images by image[y, x]
        """
        cm = camera.get_metadata()
        proj, model = cm['projection_matrix'], cm['model_matrix']
        w, h = cm['width'], cm['height']

        # get 0 to 1 coordinate for (x, y) coordinates
        xf, yf = (x + 0.5) / w, 1 - (y + 0.5) / h

        # get 0 to 1 depth value at (x,y)
        zf = depth[int(y), int(x)]

        # get the -1 to 1 (x,y,z) coordinates
        ndc = np.array([xf, yf, zf, 1]) * 2 - 1

        # transform from image space to view space
        v = np.linalg.inv(proj) @ ndc
        v /= v[3]

        # transform from view space to world space
        v = model @ v

        return v

    def pick_box(self, c):
        color, depth, segmentation = c.get_observation()

        np.random.shuffle(self.box_ids)
        for i in self.box_ids:
            m = np.where(segmentation == i)
            if len(m[0]):
                min_x = 10000
                max_x = -1
                min_y = 10000
                max_y = -1
                for y, x in zip(m[0], m[1]):
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
                x, y = round((min_x + max_x) / 2), round((min_y + max_y) / 2)
                return self.get_global_position_from_camera(c, depth, x, y)

        return False

    def bin_pos(self, c):
        color, depth, segmentation = c.get_observation()

        bin_pos = None
        m = np.where(segmentation == self.bin_id)
        if len(m[0]):
            min_x = 10000
            max_x = -1
            min_y = 10000
            max_y = -1
            for y, x in zip(m[0], m[1]):
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
            x, y = round((min_x + max_x) / 2), round((min_y + max_y) / 2)
            bin_pos = self.get_global_position_from_camera(c, depth, x, y)
        return bin_pos

    def n_box_spade(self, c):
        count = 0
        color, depth, segmentation = c.get_observation()
        np.random.shuffle(self.box_ids)
        for i in self.box_ids:
            m = np.where(segmentation == i)
            if len(m[0]):
                min_x = 10000
                max_x = -1
                min_y = 10000
                max_y = -1
                for y, x in zip(m[0], m[1]):
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
                x, y = round((min_x + max_x) / 2), round((min_y + max_y) / 2)
                world_pos = self.get_global_position_from_camera(c, depth, x, y)
                if world_pos is not False:
                    if -0.3 < world_pos[0] < 0.16 and -0.31 < world_pos[1] < 0.31 and world_pos[2] > 0.66:
                        count += 1
        return count


class SimplePID:
    def __init__(self, kp=0.0, ki=0.0, kd=0.0):
        self.p = kp
        self.i = ki
        self.d = kd
        self._cp = 0
        self._ci = 0
        self._cd = 0
        self._last_error = 0

    def compute(self, current_error, dt):
        d_error = current_error - self._last_error
        self._cp = current_error
        self._ci += current_error * dt
        if abs(self._last_error) > 0.01:
            self._cd = d_error / dt
        self._last_error = current_error
        signal = (self.p * self._cp) + (self.i * self._ci) + (self.d * self._cd)
        return signal

    def pid_forward(self, pids: list, target_pos: np.ndarray, current_pos: np.ndarray, dt: float) -> np.ndarray:
        qf = np.zeros(len(pids))
        errors = target_pos - current_pos
        for i in range(len(pids)):
            qf[i] = pids[i].compute(errors[i], dt)
        return qf


def skew(vec):
    return np.array([[0, -vec[2], vec[1]],
                     [vec[2], 0, -vec[0]],
                     [-vec[1], vec[0], 0]])


def adjoint_matrix(pose):
    adjoint = np.zeros([6, 6])
    adjoint[:3, :3] = pose[:3, :3]
    adjoint[3:6, 3:6] = pose[:3, :3]
    adjoint[3:6, 0:3] = skew(pose[:3, 3]) @ pose[:3, :3]
    return adjoint


if __name__ == '__main__':
    np.random.seed(0)
    env = FinalEnv()
    # env.run(Solution(), render=True, render_interval=5, debug=True)
    env.run(Solution(), render=True, render_interval=5)
    env.close()
