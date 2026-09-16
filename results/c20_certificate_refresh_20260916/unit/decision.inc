if (cfg_.trajectory_guard_en && machine_state_ == FOLLOW_TRAJ &&
                !refreshSafetyCertificate("main_pre")) {
                activateEmergencyBrake("main_pre_uncertified");
                return;
            }
