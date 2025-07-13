import {App, Stack, StackProps} from 'aws-cdk-lib'

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    console.log('EpsAssistMeStack is being synthesized.')
  }
}
