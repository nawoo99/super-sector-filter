First producer-only build invocation failed before compilation (exit 1):

`colcon build --packages-select mission_planner --executor sequential --parallel-workers 1 --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER_LAUNCHER=ccache --make-args -j1`

Installed colcon forwarded `-j1` to CMake, which rejected it with `CMake Error: Unknown argument -j1`. No source failure or test failure occurred. Corrected invocation uses `CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1`, without `--make-args`.
