from ...cli.parsers.core import CLInputFigure
from ..core import AnalysisFigureManagerBase
import typing
from ...io import PropagationOutput
from nastro import types as nt, graphics as ng
from ...logging import log
import traceback
from pathlib import Path

if typing.TYPE_CHECKING:
    import numpy as np


class EphemeridesResidualManager(AnalysisFigureManagerBase[CLInputFigure]):

    def __init__(self, user_input: CLInputFigure, frame: str) -> None:

        super().__init__(user_input)

        # Initialize containers for calculated and reference states
        self.cstates: dict[Path, nt.CartesianState[nt.Vector]] = {}
        self.rstates: dict[Path, nt.CartesianState[nt.Vector]] = {}
        self.epochs: dict[Path, "np.ndarray"] = {}

        # Fill containers with results
        for source in self.user_input.source_dirs:

            # Load propagation results
            results = PropagationOutput.from_file(source / "results.pkl")

            # Get propagation output in correct frame
            if frame in ("j2000", "rsw"):
                self.cstates[source] = nt.CartesianState(
                    *getattr(results, f"cstate_{frame}").T
                )
                self.rstates[source] = nt.CartesianState(
                    *getattr(results, f"rstate_{frame}").T
                )
                self.epochs[source] = results.epochs
            else:
                log.fatal(
                    f"Requested propagation output in invalid frame: {frame}"
                )
                log.fatal(traceback.extract_stack()[-2])
                exit(1)

        # # Load propagation results
        # results = PropagationOutput.from_file(self.source_dir / "results.pkl")

        # # Get propagation output in correct frame
        # if frame in ("j2000", "rsw"):

        #     self.cstate = nt.CartesianState[nt.Vector](
        #         *getattr(results, f"cstate_{frame}").T
        #     )
        #     self.rstate = nt.CartesianState[nt.Vector](
        #         *getattr(results, f"rstate_{frame}").T
        #     )

        # else:

        #     log.fatal(f"Requested propagation output in invalid frame: {frame}")
        #     log.fatal(traceback.extract_stack()[-2])
        #     exit(1)

        # Save frame choice
        self.frame = frame

        return None

    @property
    def vector_components(self) -> list[str]:

        match self.frame:

            case "j2000":
                return ["x", r"\dot x", "y", r"\dot y", "z", r"\dot z"]

            case "rsw":
                return ["r", r"\dot r", "s", r"\dot s", "w", r"\dot w"]

            case _:
                raise NotImplementedError("Unreachable")

    def propagation_residual_wrt_ephemerides_group(self) -> None:

        # Generate settings for canvas
        canvas_setup = self.generate_canvas_setup(
            f"propagation-vs-ephemerides-{self.frame}.png",
            save_in_base=True,
        )
        canvas_setup.canvas_title = (
            f"Propagation vs ephemerides :: {self.frame.upper()}"
        )

        # Generate common setup for subfigures
        subfig_setup = self.generate_figure_setup("", right_axis=False)
        legend_setup = ng.PlotSetup(legend_columns=2)

        # Initialize canvas
        with ng.Mosaic("ab;ab;ab;cd;cd;cd;ef;ef;ef;gg", canvas_setup) as canvas:

            components = ["x", "dx", "y", "dy", "z", "dz"]
            scales: list[float] = []

            # Initialize subfigures
            subfigures: dict[str, ng.BaseFigure] = {}
            for idx, label in enumerate(self.vector_components):

                # Generate settings for current subplot
                unit = "mm/s" if ((idx % 2) != 0) else "m"
                scales.append(1e3 if ((idx % 2) != 0) else 1)
                current_setup = subfig_setup.version(
                    ylabel=rf"$\Delta {label}$ [{unit}]"
                )

                # Add subfigure to list
                subfigures[components[idx]] = canvas.subplot(
                    current_setup  # , ng.DoubleAxis
                )

            # Fill subfigures with data
            dmars_present: bool = True
            for source, epochs in self.epochs.items():

                # Get source id
                source_id = self.get_directory_id(source)

                # Get dt, residuals and distance to Mars
                dt = (epochs - self.ref_epoch) / 3600.0
                residual = self.cstates[source] - self.rstates[source]
                dmars = self.rstates[source].r_mag * 1e-7

                for idx, component in enumerate(subfigures):

                    # Get subfigure and scale
                    subfig = subfigures[component]
                    scale = scales[idx]

                    # Only add legend to x subfigure
                    subfig.line(
                        dt,
                        getattr(residual, component) * scale,
                        label=source_id if component == "x" else None,
                    )
                    if not dmars_present:
                        subfig.line(
                            dt, dmars, axis="right", alpha=0.2, color="black"
                        )

                dmars_present = True

            # Add legend
            with canvas.subplot(legend_setup, ng.Legend) as legend:
                legend.add_legend(subfigures["x"])

            # Post-process subfigures
            for subfig in subfigures.values():
                subfig.common_postprocessing()
                subfig.custom_postprocessing()

        return None

    def propagation_residual_wrt_ephemerides_single(self) -> None:

        # Loop over sources
        for source, epochs in self.epochs.items():

            # Generate settings for canvas
            canvas_setup = self.generate_canvas_setup(
                f"propagation-vs-ephemerides-{self.frame}.png",
                save_in_base=False,
            )
            canvas_setup.canvas_title = (
                f"Propagation vs ephemerides :: {self.frame.upper()} "
                f":: {self.get_directory_id(source)}"
            )

            # Generate common settings for subfigures
            subfig_setup = self.generate_figure_setup("")

            # Get dt, residual and distance to Mars
            dt = (epochs - self.ref_epoch) / 3600.0
            residual = self.cstates[source] - self.rstates[source]
            dmars = self.rstates[source].r_mag * 1e-7

            # Generate figure
            with ng.Mosaic("ab;cd;ef", canvas_setup) as canvas:

                components = ["x", "dx", "y", "dy", "z", "dz"]

                for idx, label in enumerate(self.vector_components):

                    # Generate settings for current subplot
                    unit = "mm/s" if ((idx % 2) != 0) else "m"
                    scale = 1e3 if ((idx % 2) != 0) else 1
                    current_setup = subfig_setup.version(
                        ylabel=rf"$\Delta {label}$ [{unit}]"
                    )

                    # Generate subfigure
                    with canvas.subplot(current_setup, ng.DoubleAxis) as subfig:

                        subfig.line(
                            dt, getattr(residual, components[idx]) * scale
                        )
                        subfig.line(
                            dt, dmars, axis="right", alpha=0.2, color="black"
                        )

        return None

    def propagation_residual_wrt_ephemerides(self) -> None:

        if self.user_input.group_in_base:
            self.propagation_residual_wrt_ephemerides_group()
        else:
            self.propagation_residual_wrt_ephemerides_single()

        return None


# def propagation_residual_wrt_ephemerides(
#     user_input: "CLInputFigure",
#     frame: typing.Literal["rsw", "j2000"],
# ) -> None:

#     # Initialize manager
#     manager = EphemeridesResidualManager(user_input, frame)

#     # Define quantities to plot
#     dt = (manager.epochs - manager.ref_epoch) / 3600.0
#     residual = manager.cstate - manager.rstate
#     dmars = manager.rstate.r_mag * 1e-7

#     # Define settings for main figure
#     canvas_setup = ng.PlotSetup(
#         canvas_size=(8, 6),
#         canvas_title=(
#             f"Propagation vs ephemerides :: {frame.upper()} "
#             f":: {manager.get_directory_id(manager.source_dir)}"
#         ),
#         dir=manager.source_dir,
#         name=f"propagation-vs-ephemerides-{frame}.png",
#         save=manager.user_input.save,
#         show=manager.user_input.show,
#     )

#     # Define common settings for subfigure
#     subfig_setup = ng.PlotSetup(
#         xlabel=f"Hours past {manager.ref_epoch_isot}",
#         rlabel=r"$d_{mars}$ [$x10^{-7}$ m]",
#         scilimits=(-2, 3),
#     )

#     # Generate figure
#     with ng.Mosaic("ab;cd;ef", canvas_setup) as canvas:

#         components = ["x", "dx", "y", "dy", "z", "dz"]

#         for idx, label in enumerate(manager.vector_components):

#             # Generate settings for current subplot
#             unit = "m/s" if ((idx % 2) != 0) else "m"
#             current_setup = subfig_setup.version(
#                 ylabel=rf"$\Delta {label}$ [{unit}]"
#             )

#             # Generate subfigure
#             with canvas.subplot(
#                 setup=current_setup, generator=ng.DoubleAxis
#             ) as subfig:

#                 subfig.line(dt, getattr(residual, components[idx]))
#                 subfig.line(dt, dmars, axis="right", alpha=0.5)

#     return None
