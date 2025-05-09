#include "FMIUtil.h"
#include "FMI1.h"
#include "FMI1CSSimulation.h"

#define FMI_PATH_MAX 4096

#define CALL(f) do { status = f; if (status > FMIOK) goto TERMINATE; } while (0)

FMIStatus FMI1CSSimulate(const FMISimulationSettings* s) {

    FMIStatus status = FMIOK;

    fmi1Real time = s->startTime;

    FMIInstance* S = s->S;

    char fmuLocation[FMI_PATH_MAX] = "";

    CALL(FMIPathToURI(s->unzipdir, fmuLocation, FMI_PATH_MAX));

    CALL(FMI1InstantiateSlave(S,
        s->modelDescription->coSimulation->modelIdentifier,  // modelIdentifier
        s->modelDescription->instantiationToken,             // fmuGUID
        fmuLocation,                                         // fmuLocation
        "application/x-fmusim",                              // mimeType
        0.0,                                                 // timeout
        s->visible,                                          // visible
        fmi1False,                                           // interactive
        s->loggingOn                                         // loggingOn
    ));

    // set start values
    CALL(FMIApplyStartValues(S, s));
    CALL(FMIApplyInput(S, s->input, time, true, true, true));

    // initialize
    CALL(FMI1InitializeSlave(S, time, s->setStopTime, s->stopTime));

    CALL(FMISample(S, time, s->initialRecorder));

    for (unsigned long step = 0;; step++) {
        
        CALL(FMISample(S, time, s->recorder));

        const fmi1Real nextCommunicationPoint = s->startTime + (step + 1) * s->outputInterval;

        if (nextCommunicationPoint > s->stopTime && !FMIIsClose(nextCommunicationPoint, s->stopTime)) {
            break;
        }

        CALL(FMIApplyInput(S, s->input, time, true, true, true));

        const FMIStatus doStepStatus = FMI1DoStep(S, time, s->outputInterval, fmi1True);

        if (doStepStatus == fmi1Discard) {

            fmi1Boolean terminated;

            CALL(FMI1GetBooleanStatus(S, fmi1DoStepStatus, &terminated));

            if (terminated) {

                CALL(FMI1GetRealStatus(S, fmi1LastSuccessfulTime, &time));

                CALL(FMISample(S, time, s->recorder));

                break;
            }

        } else {

            CALL(doStepStatus);

            time = nextCommunicationPoint;
        }

        if (s->stepFinished && !s->stepFinished(s, time)) {
            break;
        }
    }

TERMINATE:

    if (status < FMIError) {

        const FMIStatus terminateStatus = FMI1TerminateSlave(S);

        if (terminateStatus > status) {
            status = terminateStatus;
        }
    }

    if (status != FMIFatal && S->component) {
        FMI1FreeSlaveInstance(S);
    }

    return status;
}